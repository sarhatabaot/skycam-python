#!/usr/bin/env bash
set -euo pipefail

# -------- CONFIG --------
CLI_NAME="skycam-cli"

# Where your source code lives
SOURCE_DIR="/ocs/python/skycam"

# Where uv keeps its managed environment
PROJECT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/skycam/project"

# Where the launcher goes
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/$CLI_NAME"
# ------------------------

log() { echo "[install] $*" >&2; }
die() { echo "[install][error] $*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1; }

# ---------- ensure uv ----------
ensure_uv() {
  if need uv; then
    log "Found uv"
    return
  fi

  log "uv not found; installing"
  curl -fsSL https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$PATH"

  need uv || die "uv installation failed"
}

# ---------- install project ----------
install_project() {
  [[ -d "$SOURCE_DIR" ]] || die "Source directory not found: $SOURCE_DIR"

  log "Installing project from $SOURCE_DIR into uv project"
  mkdir -p "$PROJECT_DIR"

  uv pip install --project "$PROJECT_DIR" -e "$SOURCE_DIR"
}

# ---------- install launcher ----------
install_launcher() {
  mkdir -p "$BIN_DIR"

  log "Installing launcher: $LAUNCHER"
  cat >"$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec uv run --project "$PROJECT_DIR" "$CLI_NAME" "\$@"
EOF

  chmod +x "$LAUNCHER"
}

# ---------- PATH hint ----------
path_hint() {
  if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo
    echo "[install][warn] ~/.local/bin is not on your PATH"
    echo "Add this to your shell profile:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
  fi
}

# ---------- main ----------
main() {
  ensure_uv
  install_project
  install_launcher
  path_hint

  log "Installed successfully"
  log "Run: $CLI_NAME"
}

main
