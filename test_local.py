import asyncio

import httpx

from bot.config import AIRFAIL_API_KEY, AIRFAIL_BASE_URL, AIRFAIL_MODEL, AIRFAIL_TIMEOUT


async def main():
    print(f"✅ Используем URL: {AIRFAIL_BASE_URL}")
    print(f"✅ Используем модель: '{AIRFAIL_MODEL}'")
    print(f"✅ Таймаут: {AIRFAIL_TIMEOUT} сек")

    print("Запрос к air.fail...")
    try:
        async with httpx.AsyncClient(timeout=AIRFAIL_TIMEOUT) as client:
            response = await client.post(
                AIRFAIL_BASE_URL,
                data={
                    "content": "[ИНСТРУКЦИИ]: Ты — консультант студии маникюра. Отвечай коротко, по делу, без рассуждений.\n\n[КЛИЕНТ]: Сколько стоит маникюр с покрытием?\n\n[АССИСТЕНТ]:",
                    "info": '{"version": "seed-2-1-turbo", "temperature": 0.3}',
                },
                headers={"Authorization": AIRFAIL_API_KEY},
            )
            response.raise_for_status()
            print("\n🗣 Ответ модели:")
            print(response.json())
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())
