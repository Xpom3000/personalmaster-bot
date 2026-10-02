import logging

from aiohttp import web
from aiogram import Bot

from bot import db
from bot.services import yookassa
from bot.handlers.cart import notify_owner

logger = logging.getLogger(__name__)


async def yookassa_webhook(request: web.Request) -> web.Response:
    """Приём уведомлений от YooKassa о статусе платежа."""
    raw_body = await request.read()
    headers = dict(request.headers)

    # Проверяем подпись (если задан секрет)
    if not yookassa.verify_webhook(raw_body, headers):
        logger.warning("Вебхук: неверная подпись — пропускаем")
        return web.Response(status=403)

    try:
        data = await request.json()
    except Exception:
        logger.error("Вебхук: не удалось распарсить JSON")
        return web.Response(status=400)

    event = data.get("event")  # "payment.succeeded" | "payment.canceled" | ...
    payment = data.get("object", {})
    payment_id = payment.get("id")
    status = payment.get("status")
    metadata = payment.get("metadata", {})
    order_id_str = metadata.get("order_id")

    logger.info("Вебхук: event=%s, payment_id=%s, status=%s, order_id=%s",
                event, payment_id, status, order_id_str)

    if not order_id_str:
        logger.warning("Вебхук: нет order_id в metadata")
        return web.Response(status=200)

    try:
        order_id = int(order_id_str)
    except ValueError:
        logger.error("Вебхук: order_id не число: %s", order_id_str)
        return web.Response(status=200)

    order = db.get_db().get_order(order_id)
    if order is None:
        logger.warning("Вебхук: заказ %s не найден", order_id)
        return web.Response(status=200)

    if order.status == db.STATUS_PAID:
        logger.info("Вебхук: заказ %s уже оплачен", order_id)
        return web.Response(status=200)

    if event == "payment.succeeded" and status == "succeeded":
        db.get_db().mark_order_paid(order_id)
        logger.info("Вебхук: заказ %s отмечен как оплаченный", order_id)

        bot: Bot = request.app["bot"]
        try:
            user_id = order.user_id
            await bot.send_message(
                user_id,
                f"✅ Оплата заказа №{order_id} подтверждена!\n"
                f"Сумма: {order.total:.2f} ₽\n"
                f"Спасибо за покупку!"
            )
        except Exception:
            logger.exception("Вебхук: не удалось отправить сообщение пользователю")

        try:
            await notify_owner(bot, f"Получена оплата заказа №{order_id} на {order.total:.2f} ₽ (вебхук)")
        except Exception:
            logger.exception("Вебхук: не удалось уведомить админа")

    elif event == "payment.canceled":
        logger.info("Вебхук: платёж по заказу %s отменён", order_id)

    return web.Response(status=200)
