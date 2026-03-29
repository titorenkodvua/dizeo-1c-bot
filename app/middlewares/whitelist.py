import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import Settings
from app.constants import MSG_ACCESS_DENIED

logger = logging.getLogger(__name__)


class WhitelistMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self._allowed = settings.allowed_user_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)
        if user.id not in self._allowed:
            logger.info("Access denied for user_id=%s", user.id)
            if isinstance(event, Message):
                await event.answer(MSG_ACCESS_DENIED)
            elif isinstance(event, CallbackQuery):
                await event.answer(MSG_ACCESS_DENIED, show_alert=True)
            return None
        return await handler(event, data)
