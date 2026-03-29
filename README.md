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
| `ONEC_TIMEOUT` | Таймаут HTTP к 1С (секунды) |
| `DEFAULT_LIMIT` | Лимит документов в списке РКО |

Узнать свой `user_id`: [@userinfobot](https://t.me/userinfobot).

Конфиг подхватывается из файла `.env` в корне проекта (`pydantic-settings`).

## 2. Деплой на VPS с PM2

Нужны **Git**, **Python 3.12+** (или 3.10+), **Node.js** (для PM2). Открытые порты снаружи **не обязательны**: бот сам ходит в Telegram и в 1С.

### Установка PM2 (один раз на сервере)

```bash
npm install -g pm2
```

### Развёртывание

```bash
sudo mkdir -p /var/www && sudo chown "$USER":"$USER" /var/www
cd /var/www
git clone <url-репозитория> dizeo-1c-bot
cd dizeo-1c-bot

python3.12 -m venv .venv
# или: python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt

cp .env.example .env
nano .env   # токен, whitelist, URL 1С

pm2 start ecosystem.config.cjs
pm2 logs dizeo-1c-bot --lines 50
pm2 save
pm2 startup
# выполните команду, которую выведет pm2 startup (часто с sudo)
```

Важно: **только один процесс** с этим ботом (`instances: 1` в `ecosystem.config.cjs`). Второй экземпляр даст `TelegramConflict`.

### Полезные команды PM2

```bash
pm2 status
pm2 logs dizeo-1c-bot
pm2 restart dizeo-1c-bot
pm2 stop dizeo-1c-bot
pm2 delete dizeo-1c-bot
```

### Обновление после `git pull`

```bash
cd /var/www/dizeo-1c-bot
git pull
.venv/bin/pip install -r requirements.txt
pm2 restart dizeo-1c-bot
```

## 3. Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python -m app.main
```

Или из Cursor / VS Code: конфиг **Run and Debug** «1C RKO Telegram bot» (см. `.vscode/launch.json`).

### Локально через PM2

```bash
pm2 start ecosystem.config.cjs
```

## 4. Структура проекта

- `app/main.py` — точка входа, long polling, снятие webhook
- `ecosystem.config.cjs` — конфиг PM2 для VPS
- `app/handlers/` — команды и сообщения
- `app/services/rko_service.py` — форматирование списка РКО
- `app/clients/one_c_client.py` — HTTP-клиент к 1С

## 5. Docker (по желанию)

Для long polling Docker не обязателен: достаточно venv + PM2. Если всё же нужен контейнер, в репозитории остаются `Dockerfile` и `docker-compose.yml`; запуск аналогичен обычному Python-образу (`python -m app.main`).

## 6. Переход с webhook на polling

Если у бота был зарегистрирован webhook, при старте выполнится `delete_webhook`. Проверка:

```bash
curl -s "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

Должно быть `"url":""` после снятия webhook.
