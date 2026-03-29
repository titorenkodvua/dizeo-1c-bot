/**
 * PM2: один процесс (long polling — нельзя запускать несколько инстансов с одним токеном).
 *
 * Запуск из корня репозитория (где лежит .venv и .env):
 *   pm2 start ecosystem.config.cjs
 *   pm2 save
 *   pm2 startup   # один раз, выполнить выданную команду с sudo
 */
module.exports = {
  apps: [
    {
      name: "dizeo-1c-bot",
      cwd: __dirname,
      script: ".venv/bin/python",
      args: "-m app.main",
      interpreter: "none",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      max_restarts: 20,
      min_uptime: "5s",
      max_memory_restart: "250M",
      time: true,
    },
  ],
};
