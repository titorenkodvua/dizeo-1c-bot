#!/usr/bin/env bash
# Первичный деплой на VPS: клон (если каталога ещё нет) или установка в уже склонированный репо,
# затем venv, зависимости, .env, PM2.
#
# 1) С нуля (каталог не существует или пустой, без .git):
#    ./scripts/deploy.sh https://github.com/ORG/dizeo-1c-bot.git /var/www/dizeo-1c-bot
#
# 2) Репозиторий уже склонирован вручную в /var/www/dizeo-1c-bot:
#    cd /var/www/dizeo-1c-bot && ./scripts/deploy.sh
#
# Требования: git, python3 (с venv), Node.js + pm2 в PATH.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL="${1:-}"
INSTALL_DIR="${2:-}"

usage() {
  echo "Usage:"
  echo "  $0 <git-url> <install-directory>     # clone + install"
  echo "  $0                                   # run inside existing clone (install only)"
  exit 1
}

check_tools() {
  for cmd in python3 npm; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "Error: '$cmd' not found in PATH"; exit 1; }
  done
  command -v pm2 >/dev/null 2>&1 || { echo "Error: pm2 not found. Install: npm install -g pm2"; exit 1; }
}

install_in_dir() {
  local dir="$1"
  cd "$dir"

  echo "Creating venv..."
  python3 -m venv .venv
  .venv/bin/pip install -U pip
  .venv/bin/pip install -r requirements.txt

  if [[ ! -f .env ]]; then
    cp .env.example .env
    echo ""
    echo "Created .env from .env.example — edit it, then: pm2 restart dizeo-1c-bot"
    echo ""
  fi

  if pm2 describe dizeo-1c-bot >/dev/null 2>&1; then
    echo "PM2 app 'dizeo-1c-bot' exists, restarting..."
    pm2 restart dizeo-1c-bot
  else
    pm2 start ecosystem.config.cjs
  fi

  pm2 save
  echo ""
  echo "Done. Logs: pm2 logs dizeo-1c-bot"
  echo "First time on this server: pm2 startup (run the printed command, often with sudo)"
}

# Режим: уже внутри клона, аргументов нет
if [[ -z "$REPO_URL" ]]; then
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  if [[ ! -d "$ROOT/.git" ]] || [[ ! -f "$ROOT/ecosystem.config.cjs" ]]; then
    echo "Run this from the project root after git clone, or pass: <git-url> <install-dir>"
    usage
  fi
  check_tools
  command -v git >/dev/null 2>&1 || true
  install_in_dir "$ROOT"
  exit 0
fi

# Режим: clone + install
[[ -n "$INSTALL_DIR" ]] || usage
command -v git >/dev/null 2>&1 || { echo "Error: git not found"; exit 1; }
check_tools

if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "Git repo already at $INSTALL_DIR — running install only."
  install_in_dir "$INSTALL_DIR"
  exit 0
fi

if [[ -e "$INSTALL_DIR" ]] && [[ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null || true)" ]]; then
  echo "Error: $INSTALL_DIR exists and is not empty (and has no .git)."
  exit 1
fi

mkdir -p "$(dirname "$INSTALL_DIR")"
echo "Cloning $REPO_URL -> $INSTALL_DIR"
git clone "$REPO_URL" "$INSTALL_DIR"
install_in_dir "$INSTALL_DIR"
