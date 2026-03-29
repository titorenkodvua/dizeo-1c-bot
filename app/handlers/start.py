import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.constants import MSG_WELCOME
from app.keyboards.main import main_reply_keyboard

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    logger.info("Command /start user_id=%s", message.from_user.id if message.from_user else None)
    await state.clear()
    await message.answer(MSG_WELCOME, reply_markup=main_reply_keyboard())
