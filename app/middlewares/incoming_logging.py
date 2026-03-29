import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class IncomingUpdateLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        uid = user.id if user else None
        if isinstance(event, Message) and event.text:
            preview = event.text[:200]
            logger.info("Incoming message user_id=%s text=%r", uid, preview)
        elif isinstance(event, CallbackQuery) and event.data:
            logger.info("Incoming callback user_id=%s data=%r", uid, event.data)
        return await handler(event, data)
