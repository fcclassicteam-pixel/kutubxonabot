"""
Click.uz merchant integratsiyasi.

Click "Invoice" (to'lov havolasi) usulidan foydalanamiz — foydalanuvchi
tugmani bosadi va Click sahifasida to'laydi. Click keyin bizning serverga
PREPARE va COMPLETE so'rovlarini yuboradi (webhook).

Hujjat: https://docs.click.uz
"""
import hashlib
from urllib.parse import urlencode

from config import CLICK_SERVICE_ID, CLICK_MERCHANT_ID, CLICK_SECRET_KEY, CLICK_MERCHANT_USER_ID

CLICK_PAY_URL = "https://my.click.uz/services/pay"

# Click xato kodlari
ERROR_SUCCESS = 0
ERROR_SIGN_CHECK_FAILED = -1
ERROR_INVALID_AMOUNT = -2
ERROR_ACTION_NOT_FOUND = -3
ERROR_ALREADY_PAID = -4
ERROR_USER_NOT_FOUND = -5
ERROR_TRANSACTION_NOT_FOUND = -6
ERROR_FAILED_TO_UPDATE = -7
ERROR_TRANSACTION_CANCELLED = -9


def build_pay_url(order_id: int, amount: int, return_url: str = "") -> str:
    """Foydalanuvchi to'lov qilishi uchun Click havolasini yaratadi."""
    params = {
        "service_id": CLICK_SERVICE_ID,
        "merchant_id": CLICK_MERCHANT_ID,
        "amount": amount,
        "transaction_param": order_id,  # bizning order_id — Click bu qiymatni qaytarib beradi
    }
    if return_url:
        params["return_url"] = return_url
    return f"{CLICK_PAY_URL}?{urlencode(params)}"


def _md5(*parts) -> str:
    raw = "".join(str(p) for p in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def check_prepare_signature(data: dict) -> bool:
    """PREPARE bosqichidagi sign_string ni tekshiradi."""
    sign_string = _md5(
        data.get("click_trans_id", ""),
        data.get("service_id", ""),
        CLICK_SECRET_KEY,
        data.get("merchant_trans_id", ""),
        data.get("amount", ""),
        data.get("action", ""),
        data.get("sign_time", ""),
    )
    return sign_string == data.get("sign_string")


def check_complete_signature(data: dict) -> bool:
    """COMPLETE bosqichidagi sign_string ni tekshiradi (merchant_prepare_id qatnashadi)."""
    sign_string = _md5(
        data.get("click_trans_id", ""),
        data.get("service_id", ""),
        CLICK_SECRET_KEY,
        data.get("merchant_trans_id", ""),
        data.get("merchant_prepare_id", ""),
        data.get("amount", ""),
        data.get("action", ""),
        data.get("sign_time", ""),
    )
    return sign_string == data.get("sign_string")
