import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

DB_PATH = os.getenv("DB_PATH", "kutubxonabot.db")

# ===== CLICK =====
CLICK_SERVICE_ID = os.getenv("CLICK_SERVICE_ID", "")
CLICK_MERCHANT_ID = os.getenv("CLICK_MERCHANT_ID", "")
CLICK_SECRET_KEY = os.getenv("CLICK_SECRET_KEY", "")
CLICK_MERCHANT_USER_ID = os.getenv("CLICK_MERCHANT_USER_ID", "")

# ===== PAYME =====
PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID", "")
PAYME_SECRET_KEY = os.getenv("PAYME_SECRET_KEY", "")
PAYME_TEST_MODE = os.getenv("PAYME_TEST_MODE", "true").lower() == "true"

WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8080")
# Render kabi hosting xizmatlari PORT nomli o'zgaruvchini avtomatik beradi —
# shuni ustuvor qilib olamiz, bo'lmasa WEBAPP_PORT yoki 8080 dan foydalanamiz.
WEBAPP_PORT = int(os.getenv("PORT", os.getenv("WEBAPP_PORT", "8080")))

# Har bir sahifada ko'rsatiladigan kitoblar soni
PAGE_SIZE = 6
