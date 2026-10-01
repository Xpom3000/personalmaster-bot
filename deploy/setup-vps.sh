#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/personalmaster-bot"
USER="www-data"

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git curl

sudo mkdir -p "$APP_DIR"
sudo chown -R "$USER:$USER" "$APP_DIR"

cd "$APP_DIR"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

sudo mkdir -p /var/log/personalmaster-bot
sudo touch /var/log/personalmaster-bot/bot.log
sudo chown -R "$USER:$USER" /var/log/personalmaster-bot

sudo cp "$APP_DIR/deploy/personalmaster-bot.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now personalmaster-bot
sudo systemctl status personalmaster-bot --no-pager
