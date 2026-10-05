#!/usr/bin/env bash
# ask — one-line installer (single-file path, no packaging required).
#   curl -fsSL https://raw.githubusercontent.com/sinhaKAN-ra/ask/main/install.sh | bash
#
# Installs the ask.py script to ~/.ask-cli and symlinks `ask` onto your PATH.
# Requires: python3 (3.8+). No pip, no dependencies.
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/sinhaKAN-ra/ask/main"
BASE_DIR="${HOME}/.ask-cli"
BIN_DIR="${HOME}/.local/bin"
SCRIPT="${BASE_DIR}/ask.py"
LINK="${BIN_DIR}/ask"

echo "==> Installing ask to ${BASE_DIR}"

command -v python3 >/dev/null 2>&1 || { echo "error: python3 is required (3.8+)"; exit 1; }

mkdir -p "${BASE_DIR}" "${BIN_DIR}"

echo "==> Downloading ask.py"
curl -fsSL "${REPO_RAW}/src/aolbeam_ask/ask.py" -o "${SCRIPT}"
chmod +x "${SCRIPT}"

echo "==> Linking ${LINK} -> ${SCRIPT}"
ln -sf "${SCRIPT}" "${LINK}"

# Seed an example config if none exists (never overwrites an existing one).
if [ ! -f "${BASE_DIR}/config.json" ]; then
  curl -fsSL "${REPO_RAW}/config.json.example" -o "${BASE_DIR}/config.json" || true
fi

echo
echo "==> Done."
case ":${PATH}:" in
  *":${BIN_DIR}:"*) : ;;
  *)
    echo "NOTE: ${BIN_DIR} is not on your PATH. Add this to your ~/.zshrc or ~/.bashrc:"
    echo "    export PATH=\"${BIN_DIR}:\$PATH\""
    ;;
esac
echo
echo "Next: get a free key at https://console.groq.com/keys then run:"
echo "    export GROQ_API_KEY=\"gsk_your_key\""
echo "    ask \"hello, are you working?\""
