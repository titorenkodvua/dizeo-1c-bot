import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.clients.one_c_client import OneCClient
from app.config import get_settings
from app.handlers import rko, start
from app.middlewares.incoming_logging import IncomingUpdateLoggingMiddleware
from app.middlewares.one_c_client import OneCClientMiddleware
from app.middlewares.whitelist import WhitelistMiddleware

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def run_bot() -> None:
    settings = get_settings()
    logger.info("Starting bot (long polling)")

    if not settings.allowed_user_ids:
        logger.warning(
            "TELEGRAM_ALLOWED_USER_IDS is empty — no user will pass the whitelist",
        )

    bot = Bot(token=settings.telegram_bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.update.middleware(IncomingUpdateLoggingMiddleware())
    dp.update.middleware(WhitelistMiddleware(settings))
    onec_client = OneCClient(
        base_url=settings.onec_root_url,
        username=settings.onec_username,
        password=settings.onec_password,
        timeout=settings.onec_timeout,
    )
    dp.update.middleware(OneCClientMiddleware(onec_client))

    dp.include_router(start.router)
    dp.include_router(rko.router)

    await bot.delete_webhook(drop_pending_updates=False)
    logger.info("Webhook cleared (if any); long polling active")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


def main() -> None:
    configure_logging()
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
