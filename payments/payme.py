"""
Payme (Paycom) merchant integratsiyasi.

Payme "Checkout" usulidan foydalanamiz — foydalanuvchiga havola beriladi,
u yerda to'laydi. Payme keyin bizning serverga JSON-RPC (Merchant API)
so'rovlarini yuboradi: CheckPerformTransaction, CreateTransaction,
PerformTransaction, CancelTransaction, CheckTransaction, GetStatement.

Hujjat: https://developer.help.paycom.uz
"""
import base64
from config import PAYME_MERCHANT_ID, PAYME_TEST_MODE

CHECKOUT_URL = "https://checkout.test.paycom.uz" if PAYME_TEST_MODE else "https://checkout.paycom.uz"

# Payme (JSON-RPC) xato kodlari
ERROR_INVALID_AMOUNT = -31001
ERROR_TRANSACTION_NOT_FOUND = -31003
ERROR_COULD_NOT_CANCEL = -31007
ERROR_COULD_NOT_PERFORM = -31008
ERROR_ORDER_NOT_FOUND = -31050
ERROR_ORDER_ALREADY_PAID = -31051

# Transaction holatlari
STATE_CREATED = 1
STATE_COMPLETED = 2
STATE_CANCELLED = -1
STATE_CANCELLED_AFTER_COMPLETE = -2


def build_pay_url(order_id: int, amount: int) -> str:
    """Foydalanuvchi to'lov qilishi uchun Payme havolasini yaratadi.
    Summani tiyin (so'mning 1/100) da yuborish kerak."""
    amount_tiyin = amount * 100
    raw = f"m={PAYME_MERCHANT_ID};ac.order_id={order_id};a={amount_tiyin}"
    encoded = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
    return f"{CHECKOUT_URL}/{encoded}"


def check_auth_header(auth_header: str, merchant_key: str) -> bool:
    """Payme so'rovlaridagi Basic Authorization headerini tekshiradi.
    Format: 'Basic base64(Paycom:merchant_key)'"""
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
        login, key = decoded.split(":", 1)
        return login == "Paycom" and key == merchant_key
    except Exception:
        return False


def rpc_error(request_id, code, message_uz):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": {"uz": message_uz, "ru": message_uz, "en": message_uz},
        },
    }


def rpc_result(request_id, result: dict):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}
