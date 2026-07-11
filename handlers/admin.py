from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
import keyboards as kb
from states import AddBook, SetOrderPrice
from config import ADMIN_IDS
from payments import click as click_api
from payments import payme as payme_api

router = Router()
router.message.filter(lambda message: message.from_user.id in ADMIN_IDS)
router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)


@router.message(F.text == "⚙️ Admin panel")
async def admin_panel(message: Message):
    await message.answer("Admin panel:", reply_markup=kb.admin_menu())


@router.message(F.text == "📊 Statistika")
async def stats(message: Message):
    users_count = await db.count_users()
    orders = await db.get_pending_orders()
    await message.answer(
        f"👥 Foydalanuvchilar: {users_count}\n"
        f"📋 Kutilayotgan buyurtmalar: {len(orders)}"
    )


# ---------- ADD BOOK FLOW ----------

@router.message(F.text == "➕ Kitob qo'shish")
async def add_book_start(message: Message, state: FSMContext):
    await state.set_state(AddBook.title)
    await message.answer("📖 Kitob nomini kiriting:", reply_markup=kb.cancel_kb())


@router.message(F.text == "❌ Bekor qilish", AddBook.title)
@router.message(F.text == "❌ Bekor qilish", AddBook.author)
@router.message(F.text == "❌ Bekor qilish", AddBook.genre)
@router.message(F.text == "❌ Bekor qilish", AddBook.book_type)
@router.message(F.text == "❌ Bekor qilish", AddBook.file)
@router.message(F.text == "❌ Bekor qilish", AddBook.cover)
@router.message(F.text == "❌ Bekor qilish", AddBook.description)
@router.message(F.text == "❌ Bekor qilish", AddBook.price)
@router.message(F.text == "❌ Bekor qilish", AddBook.confirm)
async def add_book_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=kb.admin_menu())


@router.message(AddBook.title)
async def add_book_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddBook.author)
    await message.answer("✍️ Muallifini kiriting (yoki \"-\"):")


@router.message(AddBook.author)
async def add_book_author(message: Message, state: FSMContext):
    author = message.text.strip()
    await state.update_data(author=None if author == "-" else author)
    await state.set_state(AddBook.genre)
    await message.answer("🏷 Janrini kiriting (masalan: Roman, Fantastika, Tarix):")


@router.message(AddBook.genre)
async def add_book_genre(message: Message, state: FSMContext):
    await state.update_data(genre=message.text.strip())
    await state.set_state(AddBook.book_type)
    await message.answer("Kitob turini tanlang:", reply_markup=kb.book_type_kb())


@router.message(AddBook.book_type, F.text.in_({"🎧 Audio", "📖 Matnli"}))
async def add_book_type(message: Message, state: FSMContext):
    book_type = "audio" if "Audio" in message.text else "text"
    await state.update_data(book_type=book_type)
    await state.set_state(AddBook.file)
    file_word = "audio faylni" if book_type == "audio" else "kitob faylini (PDF/DOCX)"
    await message.answer(f"📎 Kitobning {file_word} yuboring:", reply_markup=kb.cancel_kb())


@router.message(AddBook.file, F.audio | F.document | F.voice)
async def add_book_file(message: Message, state: FSMContext):
    data = await state.get_data()
    if data["book_type"] == "audio":
        file_id = message.audio.file_id if message.audio else message.voice.file_id
    else:
        if not message.document:
            await message.answer("Iltimos, kitob faylini hujjat (document) sifatida yuboring.")
            return
        file_id = message.document.file_id
    await state.update_data(file_id=file_id)
    await state.set_state(AddBook.cover)
    await message.answer("🖼 Muqova rasmini yuboring (yoki o'tkazib yuboring):", reply_markup=kb.skip_kb())


@router.message(AddBook.cover, F.photo)
async def add_book_cover(message: Message, state: FSMContext):
    await state.update_data(cover_file_id=message.photo[-1].file_id)
    await state.set_state(AddBook.description)
    await message.answer("📝 Kitob haqida qisqacha ma'lumot yozing (yoki \"-\"):", reply_markup=kb.cancel_kb())


@router.message(AddBook.cover, F.text == "➡️ O'tkazib yuborish")
async def add_book_cover_skip(message: Message, state: FSMContext):
    await state.update_data(cover_file_id=None)
    await state.set_state(AddBook.description)
    await message.answer("📝 Kitob haqida qisqacha ma'lumot yozing (yoki \"-\"):", reply_markup=kb.cancel_kb())


@router.message(AddBook.description)
async def add_book_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    await state.update_data(description=None if desc == "-" else desc)
    await state.set_state(AddBook.price)
    await message.answer("💰 Narxini so'mda kiriting (bepul bo'lsa 0):", reply_markup=kb.cancel_kb())


@router.message(AddBook.price)
async def add_book_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 15000 yoki 0).")
        return
    data = await state.get_data()
    await state.update_data(price=price)
    price_text = "Bepul" if price == 0 else f"{price:,} so'm".replace(",", " ")
    await message.answer(
        f"📖 <b>{data['title']}</b>\n"
        f"✍️ {data.get('author') or '-'}\n"
        f"🏷 {data['genre']}\n"
        f"Turi: {data['book_type']}\n"
        f"Narxi: {price_text}\n\n"
        f"Saqlaymizmi?",
        reply_markup=kb.confirm_kb(),
    )
    await state.set_state(AddBook.confirm)


@router.message(AddBook.confirm, F.text == "✅ Saqlash")
async def add_book_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    book_id = await db.add_book(
        title=data["title"],
        author=data.get("author"),
        genre=data["genre"],
        book_type=data["book_type"],
        description=data.get("description"),
        file_id=data["file_id"],
        cover_file_id=data.get("cover_file_id"),
        price=data["price"],
        added_by=message.from_user.id,
    )
    await state.clear()
    await message.answer(f"✅ Kitob qo'shildi! (ID: {book_id})", reply_markup=kb.admin_menu())


# ---------- ORDERS ----------

@router.message(F.text == "📋 Buyurtmalar")
async def list_orders(message: Message):
    orders = await db.get_pending_orders()
    if not orders:
        await message.answer("Hozircha yangi buyurtmalar yo'q.")
        return
    for order in orders:
        price_line = f"Narx: {order['price']} so'm" if order["price"] else "Narx: belgilanmagan"
        await message.answer(
            f"🆔 #{order['id']}\n"
            f"📖 {order['book_title']}\n"
            f"📝 {order['details']}\n"
            f"Holati: {order['status']} | To'lov: {order['payment_status']}\n"
            f"{price_line}",
            reply_markup=kb.order_admin_kb(order["id"]),
        )


@router.callback_query(F.data.startswith("setprice:"))
async def set_price_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])
    await state.update_data(order_id=order_id)
    await state.set_state(SetOrderPrice.price)
    await callback.message.answer(f"Buyurtma #{order_id} uchun narxni so'mda kiriting:")
    await callback.answer()


@router.message(SetOrderPrice.price)
async def set_price_finish(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
    except ValueError:
        await message.answer("Faqat raqam kiriting.")
        return
    data = await state.get_data()
    order_id = data["order_id"]
    await db.set_order_price(order_id, price)
    await state.clear()
    await message.answer(f"✅ Buyurtma #{order_id} uchun narx {price} so'm qilib belgilandi.")

    order = await db.get_order(order_id)
    from main import bot
    if price > 0:
        click_url = click_api.build_pay_url(order_id, price)
        payme_url = payme_api.build_pay_url(order_id, price)
        await bot.send_message(
            order["user_id"],
            f"📖 <b>{order['book_title']}</b> buyurtmangiz tayyor!\n"
            f"💰 Narxi: {price:,} so'm\n\n".replace(",", " ") +
            "To'lov usulini tanlang:",
            reply_markup=kb.payment_choice_kb(order_id),
        )
    else:
        await db.set_order_payment_status(order_id, "kerak_emas")
        await bot.send_message(order["user_id"], f"📖 <b>{order['book_title']}</b> buyurtmangiz bepul tayyorlandi!")


@router.callback_query(F.data.startswith("orderdone:"))
async def order_done(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    await db.set_order_status(order_id, "bajarildi")
    order = await db.get_order(order_id)
    from main import bot
    await bot.send_message(order["user_id"], f"✅ Buyurtmangiz (#{order_id}) bajarildi!")
    await callback.answer("Bajarildi deb belgilandi.")
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("ordercancel:"))
async def order_cancel(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    await db.set_order_status(order_id, "bekor qilindi")
    order = await db.get_order(order_id)
    from main import bot
    await bot.send_message(order["user_id"], f"🚫 Buyurtmangiz (#{order_id}) bekor qilindi.")
    await callback.answer("Bekor qilindi.")
    await callback.message.edit_reply_markup(reply_markup=None)
