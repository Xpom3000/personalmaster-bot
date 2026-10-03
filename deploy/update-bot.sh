#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/personalmaster-bot}"
BRANCH="${BRANCH:-main}"
SERVICE_NAME="${SERVICE_NAME:-personalmaster-bot}"

if [[ ! -d "$APP_DIR" ]]; then
  echo "[ERROR] Directory not found: $APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"

echo "==> Updating repository from $BRANCH"
git fetch origin
if git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
  git checkout "$BRANCH"
fi
git pull --ff-only origin "$BRANCH"

echo "==> Activating virtual environment"
if [[ ! -d "$APP_DIR/.venv" ]]; then
  echo "[ERROR] .venv not found in $APP_DIR" >&2
  exit 1
fi
source "$APP_DIR/.venv/bin/activate"

echo "==> Installing Python dependencies"
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

echo "==> Running test suite"
python -m pytest -q

echo "==> Restarting bot service"
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager --lines=20

echo "==> Recent logs"
sudo journalctl -u "$SERVICE_NAME" -n 30 --no-pager

echo "[OK] Deployment complete: $SERVICE_NAME"
