import asyncio
from openai import AsyncOpenAI
from bot.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

client = AsyncOpenAI(
    api_key="ollama",
    base_url=OLLAMA_BASE_URL,
    timeout=OLLAMA_TIMEOUT,
)

async def main():
    print(f"✅ Используем URL: {OLLAMA_BASE_URL}")
    print(f"✅ Используем модель: '{OLLAMA_MODEL}'")
    print(f"✅ Таймаут: {OLLAMA_TIMEOUT} сек")

    print("Запрос к локальной модели...")
    try:
        resp = await client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "Ты — консультант студии маникюра. Отвечай коротко, по делу, без рассуждений."},
                {"role": "user", "content": "Сколько стоит маникюр с покрытием?"},
            ],
            temperature=0.3,
        )
        print("\n🗣 Ответ модели:")
        print(resp.choices[0].message.content)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
