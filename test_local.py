import asyncio
from openai import AsyncOpenAI
from bot.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_TIMEOUT

client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    timeout=DEEPSEEK_TIMEOUT,
)

async def main():
    print(f"✅ Используем URL: {DEEPSEEK_BASE_URL}")
    print(f"✅ Используем модель: '{DEEPSEEK_MODEL}'")
    print(f"✅ Таймаут: {DEEPSEEK_TIMEOUT} сек")

    print("Запрос к DeepSeek...")
    try:
        resp = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
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
