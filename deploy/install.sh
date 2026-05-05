#!/usr/bin/env bash
# One-shot installer for a Raspberry Pi running Raspberry Pi OS (Bookworm+).
# Run from the repo root: sudo bash deploy/install.sh
set -euo pipefail

ROOT=/opt/musictoken
SERVICE_DIR=/etc/systemd/system

if [[ "$EUID" -ne 0 ]]; then
  echo "Run with sudo." >&2
  exit 1
fi

apt-get update
apt-get install -y python3-venv python3-pip i2c-tools chromium-browser \
                   libffi-dev libssl-dev vlc

mkdir -p "$ROOT"
rsync -a --delete --exclude '.venv' --exclude 'config/chips.db' \
      --exclude 'config/.spotify_cache' "$(pwd)/" "$ROOT/"

cd "$ROOT"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt -r requirements-pi.txt

cp deploy/musictoken.service       "$SERVICE_DIR/"
cp deploy/musictoken-kiosk.service "$SERVICE_DIR/"

systemctl daemon-reload
systemctl enable --now musictoken
systemctl enable --now musictoken-kiosk

echo "Installed. Check 'systemctl status musictoken'."
