import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db
from handlers import user as user_handlers
from handlers import admin as admin_handlers
from payments.server import run_webhook_server

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Admin router birinchi bo'lishi kerak, chunki u faqat ADMIN_IDS uchun filtrlangan
dp.include_router(admin_handlers.router)
dp.include_router(user_handlers.router)


async def main():
    await db.init_db()
    await run_webhook_server()  # Click/Payme webhook serverini background'da ishga tushiradi
    logging.info("Bot va to'lov serveri ishga tushdi.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
