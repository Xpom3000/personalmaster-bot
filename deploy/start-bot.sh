#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/personalmaster-bot"
VENV_DIR="$APP_DIR/.venv"
LOG_DIR="/var/log/personalmaster-bot"
mkdir -p "$LOG_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[ERROR] venv not found in $VENV_DIR" >&2
  exit 1
fi

export PYTHONUNBUFFERED=1
exec "$VENV_DIR/bin/python" "$APP_DIR/main.py" >>"$LOG_DIR/bot.log" 2>&1
