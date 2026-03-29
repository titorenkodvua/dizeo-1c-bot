from __future__ import annotations

import logging
from decimal import Decimal

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.clients.one_c_client import OneCClient, OneCClientError
from app.config import get_settings
from app.constants import (
    BTN_CANCEL,
    BTN_CREATE_RKO,
    MSG_ASK_COMMENT,
    MSG_CANCELLED,
    MSG_ENTER_SUM_COMMENT,
    MSG_INVALID_SUM,
    MSG_ONEC_UNAVAILABLE,
    MSG_ONEC_UNEXPECTED,
    BTN_SHOW_RKO,
)
from app.keyboards.main import confirmation_inline_keyboard, main_reply_keyboard
from app.services.rko_service import (
    format_confirmation_question,
    format_rko_list_messages,
)
from app.utils.parser import parse_decimal_token, split_amount_and_rest
from app.utils.validators import is_valid_rko_amount

logger = logging.getLogger(__name__)

router = Router()


class RkoStates(StatesGroup):
    waiting_line = State()
    waiting_comment = State()
    confirming = State()


def _parse_amount_line(text: str) -> tuple[Decimal | None, str, str | None]:
    first, rest = split_amount_and_rest(text)
    if not first:
        return None, "", MSG_INVALID_SUM
    amount = parse_decimal_token(first)
    if amount is None:
        return None, "", MSG_INVALID_SUM
    if not is_valid_rko_amount(amount):
        return None, "", MSG_INVALID_SUM
    return amount, rest, None


async def _send_rko_list(message: Message, onec_client: OneCClient) -> None:
    settings = get_settings()
    try:
        payload = await onec_client.get_cash_expense_orders(settings.default_limit)
    except OneCClientError as e:
        msg = MSG_ONEC_UNEXPECTED if e.kind == "parse" else MSG_ONEC_UNAVAILABLE
        await message.answer(msg, reply_markup=main_reply_keyboard())
        return
    try:
        parts = format_rko_list_messages(payload)
    except ValueError:
        await message.answer(MSG_ONEC_UNEXPECTED, reply_markup=main_reply_keyboard())
        return
    for chunk in parts:
        await message.answer(
            chunk,
            reply_markup=main_reply_keyboard(),
            parse_mode=ParseMode.HTML,
        )


async def _goto_confirmation(
    message: Message,
    state: FSMContext,
    amount: Decimal,
    comment: str,
) -> None:
    await state.set_state(RkoStates.confirming)
    await state.update_data(pending_sum=str(amount), pending_comment=comment)
    text = format_confirmation_question(amount, comment)
    await message.answer(
        text,
        reply_markup=confirmation_inline_keyboard(),
    )


@router.callback_query(F.data == "rko:confirm", StateFilter(RkoStates.confirming))
async def on_confirm_rko(
    callback: CallbackQuery,
    state: FSMContext,
    onec_client: OneCClient,
    bot: Bot,
) -> None:
    await callback.answer()
    msg = callback.message
    data = await state.get_data()
    sum_s = data.get("pending_sum")
    comment = data.get("pending_comment")
    if sum_s is None or comment is None:
        await state.clear()
        text = "Сессия устарела. Начните с команды «Создать РКО»."
        if msg:
            await msg.answer(text, reply_markup=main_reply_keyboard())
        return
    amount = Decimal(sum_s)
    try:
        body = await onec_client.create_cash_expense_order(comment, amount)
    except OneCClientError as e:
        text = MSG_ONEC_UNEXPECTED if e.kind == "parse" else MSG_ONEC_UNAVAILABLE
        await state.clear()
        if msg:
            try:
                await msg.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            await msg.answer(text, reply_markup=main_reply_keyboard())
        return
    await state.clear()
    if msg:
        try:
            await msg.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await msg.answer(body, reply_markup=main_reply_keyboard())
    elif callback.from_user:
        await bot.send_message(
            callback.from_user.id,
            body,
            reply_markup=main_reply_keyboard(),
        )


@router.callback_query(F.data == "rko:confirm")
async def on_confirm_rko_duplicate(callback: CallbackQuery) -> None:
    """Повторный callback после успеха или старое сообщение — без лишнего текста в чате."""
    await callback.answer()


@router.callback_query(F.data == "rko:cancel", StateFilter(RkoStates.confirming))
async def on_cancel_inline(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(MSG_CANCELLED, reply_markup=main_reply_keyboard())


@router.callback_query(F.data == "rko:cancel")
async def on_cancel_inline_duplicate(callback: CallbackQuery) -> None:
    await callback.answer()


@router.message(F.text == BTN_CANCEL)
async def on_cancel_reply(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(MSG_CANCELLED, reply_markup=main_reply_keyboard())


@router.message(F.text == BTN_SHOW_RKO)
async def on_show_rko(message: Message, state: FSMContext, onec_client: OneCClient) -> None:
    await state.clear()
    await _send_rko_list(message, onec_client)


@router.message(F.text == BTN_CREATE_RKO)
async def on_create_start(message: Message, state: FSMContext) -> None:
    await state.set_state(RkoStates.waiting_line)
    await message.answer(MSG_ENTER_SUM_COMMENT, reply_markup=main_reply_keyboard())


@router.message(RkoStates.waiting_line, F.text)
async def on_waiting_line(message: Message, state: FSMContext) -> None:
    amount, rest, err = _parse_amount_line(message.text or "")
    if err:
        logger.info("Validation error (waiting_line): %s", err)
        await message.answer(err, reply_markup=main_reply_keyboard())
        return
    if not rest.strip():
        await state.set_state(RkoStates.waiting_comment)
        await state.update_data(pending_sum=str(amount))
        await message.answer(MSG_ASK_COMMENT, reply_markup=main_reply_keyboard())
        return
    await _goto_confirmation(message, state, amount, rest.strip())


@router.message(RkoStates.waiting_comment, F.text)
async def on_waiting_comment(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    sum_s = data.get("pending_sum")
    if sum_s is None:
        await state.clear()
        await message.answer(MSG_CANCELLED, reply_markup=main_reply_keyboard())
        return
    comment = (message.text or "").strip()
    if not comment:
        await message.answer(MSG_ASK_COMMENT, reply_markup=main_reply_keyboard())
        return
    amount = Decimal(sum_s)
    await _goto_confirmation(message, state, amount, comment)


@router.message(RkoStates.confirming, F.text)
async def on_confirming_text(message: Message) -> None:
    await message.answer(
        "Используйте кнопки «Подтвердить» или «Отмена» под сообщением с вопросом.",
        reply_markup=main_reply_keyboard(),
    )


@router.message(StateFilter(None), F.text)
async def on_idle_quick_rko(message: Message, state: FSMContext) -> None:
    if message.text.startswith("/"):
        return
    if message.text in (BTN_SHOW_RKO, BTN_CREATE_RKO, BTN_CANCEL):
        return
    amount, rest, err = _parse_amount_line(message.text or "")
    if err:
        logger.info("Validation error (idle): %s", err)
        await message.answer(err, reply_markup=main_reply_keyboard())
        return
    if not rest.strip():
        await state.set_state(RkoStates.waiting_comment)
        await state.update_data(pending_sum=str(amount))
        await message.answer(MSG_ASK_COMMENT, reply_markup=main_reply_keyboard())
        return
    await _goto_confirmation(message, state, amount, rest.strip())
