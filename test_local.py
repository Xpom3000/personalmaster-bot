import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="test",
    base_url="http://localhost:11434/v1",
)

async def test():
    resp = await client.chat.completions.create(
        model="deepseek-r1",
        messages=[{"role": "user", "content": "Привет, ты работаешь локально?"}]
    )
    print(resp.choices[0].message.content)

asyncio.run(test())