"""
Click va Payme webhook so'rovlarini qabul qiladigan aiohttp server.
Bot bilan bir jarayonda (background task sifatida) ishga tushiriladi.
"""
from aiohttp import web

import database as db
from config import CLICK_SECRET_KEY, PAYME_SECRET_KEY, WEBAPP_PORT, ADMIN_IDS
from payments import click as click_api
from payments import payme as payme_api


async def _notify_payment_success(order):
    """To'lov muvaffaqiyatli bo'lganda foydalanuvchi va adminlarga xabar beradi."""
    from main import bot  # local import — circular importdan qochish uchun

    try:
        await bot.send_message(
            order["user_id"],
            f"✅ To'lov qabul qilindi! Buyurtma #{order['id']} ({order['book_title']}) "
            "tez orada sizga yuboriladi.",
        )
    except Exception:
        pass

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💰 Buyurtma #{order['id']} uchun to'lov qabul qilindi. "
                "Kitobni foydalanuvchiga yuborishingiz mumkin.",
            )
        except Exception:
            pass


# ============ CLICK ============

async def click_handler(request: web.Request):
    data = dict(await request.post())
    action = data.get("action")

    order_id = int(data.get("merchant_trans_id", 0) or 0)
    order = await db.get_order(order_id) if order_id else None

    if not order:
        return web.json_response({
            "error": click_api.ERROR_USER_NOT_FOUND,
            "error_note": "Buyurtma topilmadi",
        })

    if action == "0":  # PREPARE
        if not click_api.check_prepare_signature(data):
            return web.json_response({
                "error": click_api.ERROR_SIGN_CHECK_FAILED, "error_note": "Sign xato",
            })
        if int(data.get("amount", 0)) != order["price"]:
            return web.json_response({
                "error": click_api.ERROR_INVALID_AMOUNT, "error_note": "Summa mos emas",
            })

        payment_id = await db.create_payment(order_id, "click", int(float(data.get("amount", 0))))
        return web.json_response({
            "click_trans_id": data.get("click_trans_id"),
            "merchant_trans_id": order_id,
            "merchant_prepare_id": payment_id,
            "error": click_api.ERROR_SUCCESS,
            "error_note": "OK",
        })

    elif action == "1":  # COMPLETE
        if not click_api.check_complete_signature(data):
            return web.json_response({
                "error": click_api.ERROR_SIGN_CHECK_FAILED, "error_note": "Sign xato",
            })

        payment_id = int(data.get("merchant_prepare_id", 0) or 0)
        payment = await db.get_payment(payment_id)
        if not payment:
            return web.json_response({
                "error": click_api.ERROR_TRANSACTION_NOT_FOUND, "error_note": "Topilmadi",
            })

        error = int(data.get("error", 0))
        if error < 0:
            await db.mark_payment_cancelled(payment_id)
            return web.json_response({
                "click_trans_id": data.get("click_trans_id"),
                "merchant_trans_id": order_id,
                "merchant_confirm_id": payment_id,
                "error": click_api.ERROR_SUCCESS,
                "error_note": "OK",
            })

        await db.set_payment_transaction(payment_id, data.get("click_trans_id"), 2)
        await db.mark_payment_performed(payment_id)
        await db.set_order_payment_status(order_id, "tolandi", "click")
        await db.set_order_status(order_id, "jarayonda")
        await _notify_payment_success(order)

        return web.json_response({
            "click_trans_id": data.get("click_trans_id"),
            "merchant_trans_id": order_id,
            "merchant_confirm_id": payment_id,
            "error": click_api.ERROR_SUCCESS,
            "error_note": "OK",
        })

    return web.json_response({
        "error": click_api.ERROR_ACTION_NOT_FOUND, "error_note": "Amal topilmadi",
    })


# ============ PAYME ============

async def payme_handler(request: web.Request):
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    auth = request.headers.get("Authorization", "")
    if not payme_api.check_auth_header(auth, PAYME_SECRET_KEY):
        return web.json_response(
            payme_api.rpc_error(request_id, -32504, "Avtorizatsiya xato")
        )

    if method == "CheckPerformTransaction":
        order_id = int(params.get("account", {}).get("order_id", 0) or 0)
        order = await db.get_order(order_id)
        if not order:
            return web.json_response(
                payme_api.rpc_error(request_id, payme_api.ERROR_ORDER_NOT_FOUND, "Buyurtma topilmadi")
            )
        if order["payment_status"] == "tolandi":
            return web.json_response(
                payme_api.rpc_error(request_id, payme_api.ERROR_ORDER_ALREADY_PAID, "Allaqachon to'langan")
            )
        expected_amount = order["price"] * 100
        if int(params.get("amount", 0)) != expected_amount:
            return web.json_response(
                payme_api.rpc_error(request_id, payme_api.ERROR_INVALID_AMOUNT, "Summa mos emas")
            )
        return web.json_response(payme_api.rpc_result(request_id, {"allow": True}))

    elif method == "CreateTransaction":
        order_id = int(params.get("account", {}).get("order_id", 0) or 0)
        order = await db.get_order(order_id)
        if not order:
            return web.json_response(
                payme_api.rpc_error(request_id, payme_api.ERROR_ORDER_NOT_FOUND, "Buyurtma topilmadi")
            )
        trans_id = params.get("id")
        existing = await db.get_payment_by_transaction("payme", trans_id)
        if existing:
            return web.json_response(payme_api.rpc_result(request_id, {
                "create_time": 0, "transaction": str(existing["id"]),
                "state": existing["state"],
            }))
        payment_id = await db.create_payment(order_id, "payme", int(params.get("amount", 0)) // 100)
        await db.set_payment_transaction(payment_id, trans_id, payme_api.STATE_CREATED)
        return web.json_response(payme_api.rpc_result(request_id, {
            "create_time": 0, "transaction": str(payment_id),
            "state": payme_api.STATE_CREATED,
        }))

    elif method == "PerformTransaction":
        trans_id = params.get("id")
        payment = await db.get_payment_by_transaction("payme", trans_id)
        if not payment:
            return web.json_response(
                payme_api.rpc_error(request_id, payme_api.ERROR_TRANSACTION_NOT_FOUND, "Topilmadi")
            )
        if payment["status"] != "tolandi":
            await db.mark_payment_performed(payment["id"])
            await db.set_order_payment_status(payment["order_id"], "tolandi", "payme")
            await db.set_order_status(payment["order_id"], "jarayonda")
            order = await db.get_order(payment["order_id"])
            await _notify_payment_success(order)
        return web.json_response(payme_api.rpc_result(request_id, {
            "transaction": str(payment["id"]), "perform_time": 0,
            "state": payme_api.STATE_COMPLETED,
        }))

    elif method == "CancelTransaction":
        trans_id = params.get("id")
        payment = await db.get_payment_by_transaction("payme", trans_id)
        if not payment:
            return web.json_response(
                payme_api.rpc_error(request_id, payme_api.ERROR_TRANSACTION_NOT_FOUND, "Topilmadi")
            )
        new_state = (payme_api.STATE_CANCELLED_AFTER_COMPLETE
                     if payment["status"] == "tolandi" else payme_api.STATE_CANCELLED)
        await db.mark_payment_cancelled(payment["id"], new_state)
        await db.set_order_payment_status(payment["order_id"], "bekor_qilindi")
        return web.json_response(payme_api.rpc_result(request_id, {
            "transaction": str(payment["id"]), "cancel_time": 0, "state": new_state,
        }))

    elif method == "CheckTransaction":
        trans_id = params.get("id")
        payment = await db.get_payment_by_transaction("payme", trans_id)
        if not payment:
            return web.json_response(
                payme_api.rpc_error(request_id, payme_api.ERROR_TRANSACTION_NOT_FOUND, "Topilmadi")
            )
        return web.json_response(payme_api.rpc_result(request_id, {
            "create_time": 0, "perform_time": 0, "cancel_time": 0,
            "transaction": str(payment["id"]), "state": payment["state"], "reason": None,
        }))

    return web.json_response(payme_api.rpc_error(request_id, -32601, "Metod topilmadi"))


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/payments/click", click_handler)
    app.router.add_post("/payments/payme", payme_handler)
    return app


async def run_webhook_server():
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBAPP_PORT)
    await site.start()
