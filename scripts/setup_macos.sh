#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -m)" != "arm64" ]]; then
  echo "This setup is intended for an Apple Silicon (arm64) Mac."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.11 was not found. Install it with: brew install python@3.11"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel cmake

export CMAKE_ARGS="-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_APPLE_SILICON_PROCESSOR=arm64 -DGGML_METAL=on"
export FORCE_CMAKE=1
python -m pip install --upgrade --force-reinstall llama-cpp-python
python -m pip install -r backend/requirements-dev.txt

echo "macOS environment ready. Next: source .venv/bin/activate"
echo "Then download the GGUF with: python backend/download_models.py"
