#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root even if script invoked elsewhere
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="${PYTHON:-python3}"
PORT="${PORT:-8000}"
SKIP_PIP="${SKIP_PIP:-0}"

# ── Activate / create venv ────────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
  echo "[setup] Creating virtual environment..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# ── Install deps ──────────────────────────────────────────────────────────────
if [ "$SKIP_PIP" != "1" ]; then
  pip install --disable-pip-version-check -q -r "$BACKEND_DIR/requirements.txt"
fi

# ── Fix macOS Python SSL certificates (one-liner) ─────────────────────────────
# This runs the official macOS Python certificate installer if available.
SSL_INSTALLER="$(dirname "$(which python3)")/Install Certificates.command"
if [ -f "$SSL_INSTALLER" ]; then
  bash "$SSL_INSTALLER" > /dev/null 2>&1 || true
fi
# Always set certifi as fallback SSL bundle
CERTIFI_BUNDLE="$("$VENV_DIR/bin/python" -c 'import certifi; print(certifi.where())' 2>/dev/null || echo "")"
if [ -n "$CERTIFI_BUNDLE" ]; then
  export SSL_CERT_FILE="$CERTIFI_BUNDLE"
  export REQUESTS_CA_BUNDLE="$CERTIFI_BUNDLE"
fi

# ── Handle special commands ───────────────────────────────────────────────────
if [ "${1:-}" = "setup-models" ]; then
  echo "📥 Pre-downloading Florence-2 model (~1.5 GB)..."
  cd "$BACKEND_DIR"
  python -m backend.setup_models
  echo "✅ Model download complete. Run './run.sh' to start the app."
  exit 0
fi

# ── Increase HF timeout globally ──────────────────────────────────────────────
export HF_HUB_TIMEOUT=120
export HF_HUB_DOWNLOAD_TIMEOUT=120
# Uncomment to use mirror if huggingface.co is blocked:
# export HF_ENDPOINT=https://hf-mirror.com
# Uncomment to force offline (no download attempts):
# export FLORENCE_OFFLINE=true

# ── Start server ──────────────────────────────────────────────────────────────
cd "$BACKEND_DIR"
exec python -m uvicorn main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --log-level info
