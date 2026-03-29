from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.constants import BTN_CANCEL, BTN_CONFIRM, BTN_CREATE_RKO, BTN_INLINE_CANCEL, BTN_SHOW_RKO


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SHOW_RKO)],
            [KeyboardButton(text=BTN_CREATE_RKO)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def confirmation_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=BTN_CONFIRM, callback_data="rko:confirm"),
                InlineKeyboardButton(text=BTN_INLINE_CANCEL, callback_data="rko:cancel"),
            ],
        ],
    )
