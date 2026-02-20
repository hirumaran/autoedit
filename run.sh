#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root even if script invoked elsewhere
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="${PYTHON:-python3}"
LOG_LEVEL="${LOG_LEVEL:-info}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-0}"
SKIP_PIP="${SKIP_PIP:-1}"

# Ensure a local virtual environment exists so dependencies stay isolated.
if [ ! -d "$VENV_DIR" ]; then
  echo "[setup] Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# Install/refresh backend requirements unless explicitly skipped (avoids long startups).
if [ "$SKIP_PIP" != "1" ]; then
  pip install --disable-pip-version-check -r "$BACKEND_DIR/requirements.txt"
fi

cd "$BACKEND_DIR"
export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"

# Free the port if something is still holding it (common after background runs).
if lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  PIDS=$(lsof -tiTCP:"$PORT" -sTCP:LISTEN | tr '\n' ' ')
  echo "[run] Port $PORT is in use by: $PIDS"
  echo "[run] Terminating them so the dev server can start cleanly..."
  kill -9 $PIDS || true
  sleep 1
fi

UVICORN_ARGS=("--host" "0.0.0.0" "--port" "$PORT" "--log-level" "$LOG_LEVEL")
if [ "$RELOAD" = "1" ]; then
  UVICORN_ARGS+=("--reload")
fi

exec uvicorn main:app "${UVICORN_ARGS[@]}"
