#!/usr/bin/env bash
set -Eeuo pipefail

PARALAX_VERSION="v0.1.0"
PARALAX_INSTALL_DIR="${PARALAX_INSTALL_DIR:-$HOME/paralax-v0.1}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || fail "python3 is required"
command -v git >/dev/null 2>&1 || fail "git is required"
command -v node >/dev/null 2>&1 || fail "Node.js 20+ is required"
command -v npm >/dev/null 2>&1 || fail "npm is required"

python3 - <<'PY' || fail "Python 3.11+ is required"
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY

node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)' \
  || fail "Node.js 20+ is required"

if [[ -z "${WSL_DISTRO_NAME:-}" && "$(uname -s)" != "Darwin" ]]; then
  printf 'WARNING: WSL2 was not detected. This installer supports Linux/macOS/WSL2.\n'
fi

[[ ! -e "$PARALAX_INSTALL_DIR" ]] \
  || fail "Target already exists: $PARALAX_INSTALL_DIR (choose a fresh PARALAX_INSTALL_DIR)"

printf 'Installing PARALAX integration %s into %s\n' "$PARALAX_VERSION" "$PARALAX_INSTALL_DIR"

python3 "$REPOSITORY_DIR/install.py" \
  --directory "$PARALAX_INSTALL_DIR" \
  --gemini-cli

"$PARALAX_INSTALL_DIR/venv/bin/python" \
  "$PARALAX_INSTALL_DIR/repos/paralax-mcp/examples/demo.py" \
  --directory "$PARALAX_INSTALL_DIR/runtime/demo-first" \
  --policy "$PARALAX_INSTALL_DIR/repos/axionorm/examples/technical-review.yaml" \
  --opa "$PARALAX_INSTALL_DIR/runtime/opa/opa"

cp \
  "$PARALAX_INSTALL_DIR/repos/paralax-mcp/examples/project-context.json" \
  "$PARALAX_INSTALL_DIR/runtime/candidate.json"

printf '\nBootstrap completed. No Google login or private key was created.\n'
printf 'Next:\n'
printf '  cd %q\n' "$PARALAX_INSTALL_DIR"
printf '  source venv/bin/activate\n'
printf '  export PATH=%q/client/node_modules/.bin:$PATH\n' "$PARALAX_INSTALL_DIR"
printf '  gemini\n'
printf '\nAfter login, inspect and edit: %s/runtime/candidate.json\n' "$PARALAX_INSTALL_DIR"
