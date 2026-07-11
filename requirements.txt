from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from config import ADMIN_IDS


def main_menu(user_id: int) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🔍 Qidirish"), KeyboardButton(text="📚 Janrlar")],
        [KeyboardButton(text="🎧 Audio kitoblar"), KeyboardButton(text="📖 Matnli kitoblar")],
        [KeyboardButton(text="🛒 Kitob buyurtma qilish")],
        [KeyboardButton(text="ℹ️ Bot haqida")],
    ]
    if user_id in ADMIN_IDS:
        rows.append([KeyboardButton(text="⚙️ Admin panel")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="➕ Kitob qo'shish")],
        [KeyboardButton(text="📋 Buyurtmalar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="⬅️ Asosiy menyu")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True
    )


def book_type_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎧 Audio"), KeyboardButton(text="📖 Matnli")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
    )


def skip_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="➡️ O'tkazib yuborish")],
                  [KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def confirm_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Saqlash"), KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def genres_inline(genres: list[str]) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=g, callback_data=f"genre:{g}:0")] for g in genres]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def book_card_kb(book_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Baholash", callback_data=f"rate:{book_id}")],
        [InlineKeyboardButton(text="ℹ️ Batafsil", callback_data=f"info:{book_id}")],
    ])


def pagination_kb(prefix: str, key: str, offset: int, page_size: int, has_more: bool) -> InlineKeyboardMarkup:
    buttons = []
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Oldingi", callback_data=f"{prefix}:{key}:{max(0, offset - page_size)}"
        ))
    if has_more:
        nav.append(InlineKeyboardButton(
            text="Keyingi ➡️", callback_data=f"{prefix}:{key}:{offset + page_size}"
        ))
    if nav:
        buttons.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def rating_kb(book_id: int) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="⭐" * i, callback_data=f"setrate:{book_id}:{i}")]
               for i in range(5, 0, -1)]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_admin_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Narx belgilash", callback_data=f"setprice:{order_id}")],
        [InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"orderdone:{order_id}"),
         InlineKeyboardButton(text="🚫 Bekor qilish", callback_data=f"ordercancel:{order_id}")],
    ])


def payment_choice_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Click orqali to'lash", callback_data=f"pay:click:{order_id}")],
        [InlineKeyboardButton(text="💳 Payme orqali to'lash", callback_data=f"pay:payme:{order_id}")],
    ])
