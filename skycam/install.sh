#!/usr/bin/env bash
set -euo pipefail

# --- Config (can be overridden by env vars) ---
REPO="${REPO:-sarhatabaot/skycam-python}"
TAG="${TAG:-latest}"                         # e.g. "v0.1.0" or "latest"
ASSET_PREFIX="${ASSET_PREFIX:-skycam_cli}"   # dist file prefix (matches your build output)
PYTHON="${PYTHON:-python3}"
INSTALL_MODE="${INSTALL_MODE:-user}"         # user | venv
VENV_DIR="${VENV_DIR:-.venv-skycam}"
# --------------------------------------------

need() { command -v "$1" >/dev/null 2>&1 || { echo "Error: missing '$1'"; exit 1; }; }

need curl
need "$PYTHON"

tmp="$(mktemp -d)"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

fetch_release_json() {
  if [[ "$TAG" == "latest" ]]; then
    curl -fsSL "https://api.github.com/repos/$REPO/releases/latest"
  else
    curl -fsSL "https://api.github.com/repos/$REPO/releases/tags/$TAG"
  fi
}

json="$(fetch_release_json)"

# Pick wheel deterministically for linux x86_64:
# 1) skycam_cli*manylinux*|musllinux* x86_64 wheel
# 2) skycam_cli*py3-none-any wheel
# 3) any skycam_cli*.whl
# 4) else fall back to first .tar.gz
selection="$(
  printf '%s' "$json" | "$PYTHON" - <<'PY'
import json, sys, os

j = json.load(sys.stdin)

# Helpful GitHub API error reporting
if isinstance(j, dict) and "message" in j and not j.get("assets"):
    msg = j.get("message", "Unknown error")
    doc = j.get("documentation_url", "")
    sys.stderr.write(f"GitHub API error: {msg}\n")
    if doc:
        sys.stderr.write(f"See: {doc}\n")
    sys.exit(2)

assets = j.get("assets", []) or []
prefix = os.environ.get("ASSET_PREFIX", "skycam_cli")

def url_of(asset):
    return asset.get("browser_download_url", "")

def name_of(asset):
    return asset.get("name", "")

def is_wheel(n): return n.endswith(".whl")
def is_sdist(n): return n.endswith(".tar.gz")
def starts(n): return n.startswith(prefix)

wheels = [a for a in assets if is_wheel(name_of(a)) and starts(name_of(a))]
sdists = [a for a in assets if is_sdist(name_of(a))]

def pick(pred, items):
    for a in items:
        if pred(name_of(a).lower()):
            return a
    return None

# 1) manylinux/musllinux x86_64 wheels (linux x86 assumption)
a = pick(lambda n: ("manylinux" in n or "musllinux" in n) and ("x86_64" in n or "amd64" in n), wheels)
# 2) py3-none-any
if a is None:
    a = pick(lambda n: "py3-none-any.whl" in n or "none-any.whl" in n, wheels)
# 3) any prefix wheel
if a is None and wheels:
    a = wheels[0]

artifact_type = "wheel"
if a is None:
    artifact_type = "sdist"
    a = sdists[0] if sdists else None

if a is None:
    sys.stderr.write(f"Error: no .whl or .tar.gz assets found on this release for prefix '{prefix}'.\n")
    sys.exit(4)

print(f"{url_of(a)}\t{name_of(a)}\t{artifact_type}")
PY
)"

artifact_url="$(printf '%s' "$selection" | cut -f1)"
artifact_name="$(printf '%s' "$selection" | cut -f2)"
artifact_type="$(printf '%s' "$selection" | cut -f3)"

if [[ -z "$artifact_url" || -z "$artifact_name" ]]; then
  echo "Error: failed to select an installable artifact."
  exit 1
fi

artifact="$tmp/$artifact_name"
echo "Selected $artifact_type: $artifact_name"
echo "Downloading: $artifact_url"
curl -fL --retry 3 --retry-delay 1 -o "$artifact" "$artifact_url"

echo "Installing: $artifact_name"

ensure_pip() {
  if "$PYTHON" -m pip --version >/dev/null 2>&1; then
    return 0
  fi
  echo "pip not found for $PYTHON; attempting ensurepip..."
  "$PYTHON" -m ensurepip --upgrade >/dev/null 2>&1 || true
  "$PYTHON" -m pip --version >/dev/null 2>&1 || {
    echo "Error: pip is not available for $PYTHON."
    exit 1
  }
}
ensure_pip

if [[ "$INSTALL_MODE" == "user" ]]; then
  set +e
  "$PYTHON" -m pip install --user "$artifact"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    echo "Installed successfully."
    echo "If 'skycam' isn't found, ensure ~/.local/bin is on your PATH."
    exit 0
  fi
  echo "User install failed (common on externally-managed Python / PEP 668)."
  echo "Retry with: INSTALL_MODE=venv $0"
  exit 1
fi

if [[ "$INSTALL_MODE" == "venv" ]]; then
  "$PYTHON" -m venv "$VENV_DIR"
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
  python -m pip install --upgrade pip
  python -m pip install "$artifact"
  echo "Installed into venv: $VENV_DIR"
  echo "Run: $VENV_DIR/bin/skycam"
  exit 0
fi

echo "Error: INSTALL_MODE must be 'user' or 'venv'."
exit 1
