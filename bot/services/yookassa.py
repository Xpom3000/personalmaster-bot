import base64
import hashlib
import hmac
import logging
import uuid
from typing import Any

import httpx

from bot import config

logger = logging.getLogger(__name__)


def _auth_header() -> str:
    pair = f"{config.YOOKASSA_SHOP_ID}:{config.YOOKASSA_SECRET_KEY}"
    return "Basic " + base64.b64encode(pair.encode("utf-8")).decode("ascii")


async def _request(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not config.YOOKASSA_SHOP_ID or not config.YOOKASSA_SECRET_KEY:
        raise RuntimeError("Не заданы YOOKASSA_SHOP_ID или YOOKASSA_SECRET_KEY")

    url = f"https://api.yookassa.ru/{path.lstrip('/')}"
    headers = {
        "Authorization": _auth_header(),
        "Content-Type": "application/json",
        "Idempotence-Key": str(uuid.uuid4()),
    }

    logger.info("→ %s %s", method, url)
    if json_body:
        logger.info("  payload: %s", json_body)

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.request(method, url, headers=headers, json=json_body)

        logger.info("← %s", response.status_code)

        if response.status_code >= 400:
            logger.error("  тело ошибки: %s", response.text)
            response.raise_for_status()

        return response.json()


async def create_payment_for_order(order: Any) -> tuple[str, str]:
    """Создать платёж на сумму заказа и вернуть (payment_id, payment_url)."""
    payload = {
        "amount": {"value": f"{order.total:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": config.YOOKASSA_RETURN_URL,
        },
        "description": f"Заказ № {order.id}",
        "metadata": {"order_id": str(order.id)},
    }
    data = await _request("POST", "/v3/payments", json_body=payload)
    payment_id = data["id"]
    payment_url = data["confirmation"]["confirmation_url"]
    logger.info("Платёж создан: id=%s, url=%s", payment_id, payment_url)
    return payment_id, payment_url


async def check_payment_status(payment_id: str) -> str:
    """Вернуть статус оплаты: 'pending' | 'succeeded' | 'canceled' | ..."""
    data = await _request("GET", f"/v3/payments/{payment_id}")
    status = data.get("status", "pending")
    logger.info("Статус платежа %s: %s", payment_id, status)
    return status


def verify_webhook(raw_body: bytes, headers: dict[str, str]) -> bool:
    """Проверить подпись вебхука от ЮKassa."""
    ip = headers.get("X-Real-IP") or headers.get("X-Forwarded-For", "")
    # ЮKassa шлёт уведомления с диапазона IP — можно проверить при необходимости
    # Основная проверка — по подписи, если настроена в кабинете

    # Если вебхук-секрет не задан — пропускаем проверку (для локальной разработки)
    secret = getattr(config, "YOOKASSA_WEBHOOK_SECRET", None)
    if not secret:
        logger.warning("YOOKASSA_WEBHOOK_SECRET не задан — подпись не проверяется")
        return True

    signature = headers.get("X-Request-Signature", "")
    if not signature:
        return False

    computed = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, computed)
