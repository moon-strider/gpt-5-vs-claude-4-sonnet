from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def approval_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Approve", callback_data="APR"), InlineKeyboardButton(text="❌ Reject", callback_data="REJ")]])


def disabled_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Approved ✅", callback_data="APR_DISABLED"), InlineKeyboardButton(text="Rejected ❌", callback_data="REJ_DISABLED")]])

