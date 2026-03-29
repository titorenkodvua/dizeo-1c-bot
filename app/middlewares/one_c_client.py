from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.clients.one_c_client import OneCClient


class OneCClientMiddleware(BaseMiddleware):
    def __init__(self, client: OneCClient) -> None:
        self._client = client

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["onec_client"] = self._client
        return await handler(event, data)
