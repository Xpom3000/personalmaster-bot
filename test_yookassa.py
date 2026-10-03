import asyncio
import base64
import logging
import os
import uuid

import httpx
import pytest
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Ключи тестового магазина берутся из .env (YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY) — в код их не вписываем
load_dotenv()
SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "").strip()
SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "").strip()

pytestmark = pytest.mark.skipif(not SHOP_ID or not SECRET_KEY, reason="Нужны YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY")

async def _run_payment_test():
    url = "https://api.yookassa.ru/v3/payments"

    payload = {
        "amount": {
            "value": 100.0,
            "currency": "RUB"
        },
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": "https://example.com/success"
        },
        "description": "Локальный тест платежа"
    }

    # Формируем Basic Auth вручную: SHOP_ID:SECRET_KEY -> base64
    auth_string = f"{SHOP_ID}:{SECRET_KEY}"
    auth_bytes = auth_string.encode("utf-8")
    auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_b64}",
        "Idempotence-Key": str(uuid.uuid4())
    }
    logger.info("SHOP_ID: [%s]", SHOP_ID)
    logger.info("SECRET_KEY начинается с: [%s...]", SECRET_KEY[:10] if len(SECRET_KEY) > 10 else "слишком короткий")
    logger.info("Authorization header: Basic %s", auth_b64[:20] + "...")

    logger.info("Отправляем запрос к YooKassa...")
    logger.info("Payload: %s", payload)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers=headers)

        logger.info("Статус ответа: %s", resp.status_code)
        logger.info("Тело ответа: %s", resp.text)

        if resp.status_code == 200:
            data = resp.json()
            logger.info("✅ Платёж создан!")
            logger.info("payment_id: %s", data.get("id"))
            logger.info("confirmation_url: %s", data.get("confirmation", {}).get("confirmation_url"))
        else:
            logger.error("❌ Ошибка при создании платежа")


def test_payment():
    asyncio.run(_run_payment_test())


if __name__ == "__main__":
    test_payment()
