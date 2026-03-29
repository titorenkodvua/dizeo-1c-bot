#!/usr/bin/env bash
# Обновление с Git: pull, pip install, перезапуск PM2.
#
# Запускать из корня репозитория:
#   ./scripts/update.sh
#
# Или из любого места, указав корень проекта:
#   ./scripts/update.sh /var/www/dizeo-1c-bot

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${1:-$(cd "$SCRIPT_DIR/.." && pwd)}"

cd "$ROOT"

if [[ ! -f ecosystem.config.cjs ]]; then
  echo "Error: ecosystem.config.cjs not found in $ROOT"
  exit 1
fi

if [[ ! -d .git ]]; then
  echo "Error: $ROOT is not a git repository"
  exit 1
fi

if [[ ! -x .venv/bin/pip ]]; then
  echo "Error: .venv not found or broken. Run deploy.sh or: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "Git pull in $ROOT ..."
git pull

echo "pip install ..."
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt

if pm2 describe dizeo-1c-bot >/dev/null 2>&1; then
  echo "pm2 restart dizeo-1c-bot ..."
  pm2 restart dizeo-1c-bot
else
  echo "PM2 app 'dizeo-1c-bot' not found. Start with: pm2 start ecosystem.config.cjs"
  exit 1
fi

echo "Done. Logs: pm2 logs dizeo-1c-bot --lines 30"
