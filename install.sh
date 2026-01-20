#!/usr/bin/env bash
set -euo pipefail

# --- Config (can be overridden by env vars) ---
REPO="${REPO:-sarhatabaot/skycam-python}"
TAG="${TAG:-latest}"                         # "0.1.0" or "latest"
ASSET_PREFIX="${ASSET_PREFIX:-skycam_cli}"   # expected dist prefix
PYTHON="${PYTHON:-python3}"
INSTALL_MODE="${INSTALL_MODE:-user}"         # user | venv
VENV_DIR="${VENV_DIR:-.venv-skycam}"
# --------------------------------------------

# ---------- Pretty logging ----------
log()  { printf '[install] %s\n' "$*" >&2; }
warn() { printf '[install][warn] %s\n' "$*" >&2; }
die()  { printf '[install][error] %s\n' "$*" >&2; exit 1; }

need() {
  command -v "$1" >/dev/null 2>&1 || die "Missing dependency: '$1'"
}

# Print the exact command + line on failure (helps a lot)
on_err() {
  local exit_code=$?
  local line_no=$1
  local cmd=${2:-}
  printf '\n[install][error] Failed at line %s (exit=%s)\n' "$line_no" "$exit_code" >&2
  if [[ -n "$cmd" ]]; then
    printf '[install][error] Command: %s\n' "$cmd" >&2
  fi
  printf '[install][error] Tip: re-run with: bash -x install.sh ...  (or set DEBUG=1)\n\n' >&2
  exit "$exit_code"
}
trap 'on_err ${LINENO} "$BASH_COMMAND"' ERR

# Optional debug tracing
if [[ "${DEBUG:-0}" == "1" ]]; then
  set -x
fi

need curl
need "$PYTHON"

tmp="$(mktemp -d)"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

# ---------- Helpers ----------
curl_to_file() {
  # Usage: curl_to_file <url> <outfile>
  local url="$1"
  local out="$2"

  # We want BOTH the HTTP code and the body for diagnostics.
  # -sS keeps errors, -L follows redirects
  local code
  code="$(curl -sS -L -o "$out" -w "%{http_code}" "$url")" || {
    die "Network error while requesting: $url"
  }
  printf '%s' "$code"
}

github_api_get() {
  # Usage: github_api_get <url> <outfile>
  # Adds Accept header. Also supports optional token if user sets GITHUB_TOKEN.
  local url="$1"
  local out="$2"
  local code

  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    code="$(curl -sS -L \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer $GITHUB_TOKEN" \
      -o "$out" -w "%{http_code}" "$url")" || {
        die "Network error while requesting GitHub API: $url"
      }
  else
    code="$(curl -sS -L \
      -H "Accept: application/vnd.github+json" \
      -o "$out" -w "%{http_code}" "$url")" || {
        die "Network error while requesting GitHub API: $url"
      }
  fi

  printf '%s' "$code"
}

print_github_api_error() {
  # Usage: print_github_api_error <bodyfile>
  local bodyfile="$1"
  "$PYTHON" - <<'PY' <"$bodyfile" 2>/dev/null || true
import json,sys
try:
    j=json.load(sys.stdin)
    msg=j.get("message")
    doc=j.get("documentation_url")
    if msg:
        print(f"[install][error] GitHub API message: {msg}", file=sys.stderr)
    if doc:
        print(f"[install][error] GitHub API docs: {doc}", file=sys.stderr)
except Exception:
    pass
PY
}

fetch_release_json() {
  # Writes a JSON object describing the chosen release into $tmp/release.json
  local out="$tmp/release.json"
  local code url

  if [[ "$TAG" == "latest" ]]; then
    log "Step 1/4: Fetching release metadata (TAG=latest) from GitHub API..."

    url="https://api.github.com/repos/$REPO/releases/latest"
    code="$(github_api_get "$url" "$out")"

    if [[ "$code" == "200" ]]; then
      log "Fetched latest release metadata successfully."
      return 0
    fi

    # If latest returns 404, fallback to list releases
    if [[ "$code" == "404" ]]; then
      warn "GitHub API /releases/latest returned 404."
      warn "Falling back to: /releases?per_page=1 (most recent release in list)."

      local list_out="$tmp/releases_list.json"
      url="https://api.github.com/repos/$REPO/releases?per_page=1"
      code="$(github_api_get "$url" "$list_out")"

      if [[ "$code" != "200" ]]; then
        die "Failed to list releases (HTTP $code) from: $url"
      fi

      # Convert array -> first object
      "$PYTHON" - <<'PY' <"$list_out" >"$out"
import json,sys
arr=json.load(sys.stdin)
if not arr:
    raise SystemExit("No releases found in /releases list.")
print(json.dumps(arr[0]))
PY
      log "Using most recent release from releases list."
      return 0
    fi

    # Other errors (rate limit etc.)
    warn "GitHub API /releases/latest returned HTTP $code."
    print_github_api_error "$out"
    if [[ "$code" == "403" ]]; then
      warn "If you're rate-limited, try: export GITHUB_TOKEN=... (a GitHub personal access token)."
    fi
    die "Cannot fetch release metadata."
  fi

  # Explicit tag
  log "Step 1/4: Fetching release metadata for TAG='$TAG' from GitHub API..."
  url="https://api.github.com/repos/$REPO/releases/tags/$TAG"
  code="$(github_api_get "$url" "$out")"
  if [[ "$code" != "200" ]]; then
    warn "GitHub API returned HTTP $code for: $url"
    print_github_api_error "$out"
    die "Cannot fetch release metadata for TAG='$TAG'."
  fi
  log "Fetched release metadata successfully."
}

select_artifact() {
  # Reads $tmp/release.json, outputs three tab-separated fields:
  #   artifact_url<TAB>artifact_name<TAB>artifact_type
  #
  # Linux x86_64 selection order:
  # 1) prefix + (manylinux|musllinux) + (x86_64|amd64) wheel
  # 2) prefix + py3-none-any wheel
  # 3) any prefix wheel
  # 4) sdist (.tar.gz)
  local in="$tmp/release.json"

  log "Step 2/4: Selecting artifact (prefix='$ASSET_PREFIX', linux x86_64)..."

  "$PYTHON" - <<'PY' <"$in"
import json, sys, os

j = json.load(sys.stdin)
assets = j.get("assets") or []
prefix = os.environ.get("ASSET_PREFIX", "skycam_cli")

def name(a): return a.get("name","")
def url(a):  return a.get("browser_download_url","")

wheels = [a for a in assets if name(a).startswith(prefix) and name(a).endswith(".whl")]
sdists = [a for a in assets if name(a).endswith(".tar.gz")]

def pick(pred, items):
    for a in items:
        if pred(name(a).lower()):
            return a
    return None

chosen = pick(lambda n: ("manylinux" in n or "musllinux" in n) and ("x86_64" in n or "amd64" in n), wheels)
atype = "wheel"

if chosen is None:
    chosen = pick(lambda n: "py3-none-any.whl" in n or "none-any.whl" in n, wheels)
if chosen is None and wheels:
    chosen = wheels[0]

if chosen is None:
    atype = "sdist"
    chosen = sdists[0] if sdists else None

if chosen is None:
    # Print assets list for debugging
    sys.stderr.write("[install][error] No suitable assets found on this release.\n")
    sys.stderr.write(f"[install][error] Expected: '{prefix}*.whl' (preferred) or any '.tar.gz'.\n")
    sys.stderr.write("[install][error] Assets on this release were:\n")
    for a in assets:
        sys.stderr.write(f"  - {name(a)}\n")
    sys.exit(4)

print(f"{url(chosen)}\t{name(chosen)}\t{atype}")
PY
}

download_artifact() {
  local artifact_url="$1"
  local artifact_name="$2"
  local out="$tmp/$artifact_name"

  log "Step 3/4: Downloading artifact..."
  log "  URL:  $artifact_url"
  log "  File: $artifact_name"

  # Use -f to fail on non-2xx; keep retries
  curl -fL --retry 3 --retry-delay 1 -o "$out" "$artifact_url" || {
    die "Failed to download artifact from: $artifact_url"
  }

  printf '%s' "$out"
}

ensure_pip() {
  if "$PYTHON" -m pip --version >/dev/null 2>&1; then
    return 0
  fi
  warn "pip not found for $PYTHON; attempting ensurepip..."
  "$PYTHON" -m ensurepip --upgrade >/dev/null 2>&1 || true
  "$PYTHON" -m pip --version >/dev/null 2>&1 || die "pip is not available for $PYTHON."
}

install_artifact() {
  local artifact_path="$1"
  local artifact_name
  artifact_name="$(basename "$artifact_path")"

  log "Step 4/4: Installing '$artifact_name' (mode=$INSTALL_MODE)..."
  ensure_pip

  if [[ "$INSTALL_MODE" == "user" ]]; then
    if "$PYTHON" -m pip install --user "$artifact_path"; then
      log "Installed successfully (user)."
      log "If 'skycam' isn't found, ensure ~/.local/bin is on your PATH."
      return 0
    fi
    warn "User install failed (common on externally-managed Python / PEP 668)."
    warn "Try: INSTALL_MODE=venv $0"
    return 1
  fi

  if [[ "$INSTALL_MODE" == "venv" ]]; then
    "$PYTHON" -m venv "$VENV_DIR"
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
    python -m pip install --upgrade pip
    python -m pip install "$artifact_path"
    log "Installed into venv: $VENV_DIR"
    log "Run: $VENV_DIR/bin/skycam"
    return 0
  fi

  die "INSTALL_MODE must be 'user' or 'venv' (got '$INSTALL_MODE')."
}

# ---------- Main ----------
log "Repo: $REPO"
log "Tag:  $TAG"
log "Prefix: $ASSET_PREFIX"

fetch_release_json

selection="$(select_artifact)"
artifact_url="$(printf '%s' "$selection" | cut -f1)"
artifact_name="$(printf '%s' "$selection" | cut -f2)"
artifact_type="$(printf '%s' "$selection" | cut -f3)"

log "Selected: $artifact_type -> $artifact_name"

artifact_path="$(download_artifact "$artifact_url" "$artifact_name")"
install_artifact "$artifact_path"
