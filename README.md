# Telegram-бот для РКО (1С)

Внутренний бот на **Python 3.12**, **aiogram 3**, **httpx**. Обновления от Telegram приходят через **long polling** (публичный URL и вебхук не нужны). База данных не используется.

При старте вызывается `delete_webhook`, чтобы снять старый webhook у Bot API — иначе polling не получает апдейты.

## 1. Переменные окружения

Скопируйте `.env.example` в `.env` и заполните:

| Переменная | Назначение |
|------------|------------|
| `TELEGRAM_BOT_TOKEN` | Токен от [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_ALLOWED_USER_IDS` | Список `user_id` через запятую |
| `ONEC_BASE_URL` | Базовый URL сервера 1С (без учётных данных в URL) |
| `ONEC_API_PATH` | Путь HTTP-сервиса, например `/1capi/hs/botapi` |
| `ONEC_USERNAME` / `ONEC_PASSWORD` | Basic Auth к 1С |
| `ONEC_TIMEOUT` | Таймаут HTTP к 1С (секунды). После простоя первый запрос через Keenetic/https может занимать 15–30+ с — при малом значении будет «1С недоступна» |
| `DEFAULT_LIMIT` | Лимит документов в списке РКО |

Узнать свой `user_id`: [@userinfobot](https://t.me/userinfobot).

Конфиг подхватывается из файла `.env` в корне проекта (`pydantic-settings`).

## 2. Деплой на VPS с PM2

Нужны **Git**, **Python 3.10+**, **Node.js** (для PM2). Порты наружу открывать не обязательно.

### Установка PM2 (один раз на сервере)

```bash
npm install -g pm2
```

### Скрипты

| Скрипт | Назначение |
|--------|------------|
| `scripts/deploy.sh` | Первый запуск: клон + venv + `pip` + `.env` из примера + PM2 |
| `scripts/update.sh` | Обновление: `git pull` + `pip` + `pm2 restart` |

Сделайте исполняемыми при необходимости: `chmod +x scripts/*.sh`

**Вариант A — один раз с пустого VPS** (каталога ещё нет):

```bash
sudo mkdir -p /var/www && sudo chown "$USER":"$USER" /var/www
# скопируйте deploy.sh на сервер ИЛИ сделайте одноразовый clone только скрипта:
cd /var/www
git clone --depth 1 https://github.com/ВАШ_ОРГ/dizeo-1c-bot.git dizeo-1c-bot-tmp
./dizeo-1c-bot-tmp/scripts/deploy.sh https://github.com/ВАШ_ОРГ/dizeo-1c-bot.git /var/www/dizeo-1c-bot
rm -rf dizeo-1c-bot-tmp
```

Проще: **клон вручную**, затем установка из репозитория:

```bash
cd /var/www
git clone https://github.com/ВАШ_ОРГ/dizeo-1c-bot.git
cd dizeo-1c-bot
./scripts/deploy.sh
```

`./scripts/deploy.sh` без аргументов создаёт `.venv`, ставит зависимости, копирует `.env.example` → `.env` при отсутствии `.env`, запускает или перезапускает PM2.

**Вариант B — clone + путь одной командой:**

```bash
./scripts/deploy.sh https://github.com/ВАШ_ОРГ/dizeo-1c-bot.git /var/www/dizeo-1c-bot
```

После первого запуска отредактируйте `.env`, затем:

```bash
pm2 restart dizeo-1c-bot
```

Один раз на сервере: `pm2 startup` и выполните выведенную команду (часто с `sudo`).

**Обновление после пуша в GitHub:**

```bash
/var/www/dizeo-1c-bot/scripts/update.sh
```

или `cd /var/www/dizeo-1c-bot && ./scripts/update.sh`

Важно: **только один** процесс с этим ботом — иначе `TelegramConflict`.

### Полезные команды PM2

```bash
pm2 status
pm2 logs dizeo-1c-bot
pm2 restart dizeo-1c-bot
pm2 stop dizeo-1c-bot
pm2 delete dizeo-1c-bot
```

### Развёртывание вручную (без скриптов)

```bash
cd /var/www
git clone <url> dizeo-1c-bot && cd dizeo-1c-bot
python3 -m venv .venv
.venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env
pm2 start ecosystem.config.cjs && pm2 save && pm2 startup
```

## 3. Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python -m app.main
```

Или из Cursor / VS Code: **Run and Debug** «1C RKO Telegram bot» (`.vscode/launch.json`).

### Локально через PM2

```bash
pm2 start ecosystem.config.cjs
```

## 4. Структура проекта

- `app/main.py` — точка входа, long polling, снятие webhook
- `ecosystem.config.cjs` — конфиг PM2 для VPS
- `scripts/deploy.sh` — первичный деплой
- `scripts/update.sh` — обновление с Git (`pull`, `pip`, `pm2 restart`)
- `app/handlers/` — команды и сообщения
- `app/services/rko_service.py` — форматирование списка РКО
- `app/clients/one_c_client.py` — HTTP-клиент к 1С

## 5. Docker (по желанию)

Для long polling Docker не обязателен: достаточно venv + PM2. В репозитории могут оставаться `Dockerfile` и `docker-compose.yml`.

## 6. Переход с webhook на polling

При старте выполнится `delete_webhook`. Проверка:

```bash
curl -s "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

Должно быть `"url":""`.
