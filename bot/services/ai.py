from openai import AsyncOpenAI

from bot.config import (
    BASE_DIR,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
)

# DeepSeek совместим с OpenAI SDK — меняется только base_url.
_client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=60)


def build_system_prompt() -> str:
    """Системный промпт + база знаний. Читается один раз при старте бота."""
    prompt = (BASE_DIR / "prompts" / "system_prompt.md").read_text(encoding="utf-8")
    knowledge = (BASE_DIR / "knowledge" / "personal_master.md").read_text(encoding="utf-8")
    return prompt.replace("{knowledge}", knowledge.strip())


SYSTEM_PROMPT = build_system_prompt()


async def ask(question: str) -> str:
    """Отправить вопрос в DeepSeek (с базой знаний студии) и вернуть ответ модели."""
    response = await _client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.3,
    )
    return (response.choices[0].message.content or "").strip()
