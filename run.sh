#!/usr/bin/env bash
set -euo pipefail

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
BACKEND_DIR="$SCRIPT_DIR/backend"

# ── Hugging Face & macOS env vars (set BEFORE any Python) ────────────────────
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_DISABLE_PROGRESS_BARS=0
export HF_TRANSFER_ENABLE=1
export TOKENIZERS_PARALLELISM=false
# Set to 1 to force offline mode (no network attempts at all)
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-0}"

# Florence-2 model — override with your local path if downloaded manually
export FLORENCE_MODEL_ID="${FLORENCE_MODEL_ID:-microsoft/Florence-2-base}"
export FLORENCE_LOCAL_PATH="${FLORENCE_LOCAL_PATH:-}"

# Suppress macOS ObjC fork-safety warnings
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Fix macOS SSL to use certifi bundle
export SSL_CERT_FILE="$VENV_DIR/lib/python3.11/site-packages/certifi/cacert.pem"
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"

# Python path so 'import backend' works everywhere
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo "▶  $*"; }
ok()   { echo "✅ $*"; }
warn() { echo "⚠️  $*"; }
err()  { echo "❌ $*" >&2; exit 1; }

activate_venv() {
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        err "Virtual environment not found at $VENV_DIR. Run: python3 -m venv $VENV_DIR"
    fi
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    ok "venv activated: $VIRTUAL_ENV"
}

check_ssl_cert() {
    local cert_path
    cert_path="$(python - <<'PYEOF'
import ssl, certifi, os
p = certifi.where()
print(p if os.path.exists(p) else "")
PYEOF
)"
    if [ -n "$cert_path" ]; then
        export SSL_CERT_FILE="$cert_path"
        export REQUESTS_CA_BUNDLE="$cert_path"
        ok "SSL cert: $cert_path"
    else
        warn "certifi cert not found — SSL may fail. Run: pip install -U certifi"
    fi
}

# ── Subcommands ───────────────────────────────────────────────────────────────
cmd_install() {
    activate_venv
    log "Installing/upgrading dependencies..."
    pip install --upgrade pip setuptools wheel
    pip install -r "$SCRIPT_DIR/requirements.txt"
    ok "Dependencies installed."
}

cmd_setup_models() {
    activate_venv
    check_ssl_cert
    log "Setting up Florence-2 model (ID: $FLORENCE_MODEL_ID)..."
    python - <<'PYEOF'
import sys, os
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
from backend.utils.model_manager import ensure_florence_model
ensure_florence_model()
PYEOF
    ok "Model setup complete."
}

cmd_start() {
    activate_venv
    check_ssl_cert
    log "Starting AI Video Editor backend..."
    log "  PYTHONPATH : $PYTHONPATH"
    log "  HF_ENDPOINT: $HF_ENDPOINT"
    log "  Offline    : $HF_HUB_OFFLINE"

    exec uvicorn backend.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --reload-dir "$BACKEND_DIR" \
        --log-level info
}

cmd_dev() {
    # Start frontend + backend concurrently (assumes npm concurrently)
    activate_venv
    check_ssl_cert
    log "Starting full dev stack..."
    # backend in background
    (cmd_start) &
    BACKEND_PID=$!
    # frontend
    cd "$SCRIPT_DIR" && npm run dev:frontend 2>/dev/null || true
    wait "$BACKEND_PID"
}

# ── Dispatch ──────────────────────────────────────────────────────────────────
COMMAND="${1:-start}"
case "$COMMAND" in
    install)       cmd_install ;;
    setup-models)  cmd_setup_models ;;
    start)         cmd_start ;;
    dev)           cmd_dev ;;
    *)
        echo "Usage: $0 {install|setup-models|start|dev}"
        echo ""
        echo "  install       — install Python dependencies"
        echo "  setup-models  — download/verify Florence-2 model"
        echo "  start         — start FastAPI server"
        echo "  dev           — start full stack (frontend + backend)"
        exit 1
        ;;
esac
