import re

import httpx
from openai import AsyncOpenAI

from bot.config import (
    BASE_DIR,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT,
)

USE_DEEPSEEK = True
_MODEL_NAME = DEEPSEEK_MODEL
_BASE_URL = DEEPSEEK_BASE_URL
_TIMEOUT = DEEPSEEK_TIMEOUT

_client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=_BASE_URL, timeout=_TIMEOUT)


def build_system_prompt() -> str:
    """Системный промпт + база знаний. Читается один раз при старте бота."""
    prompt = (BASE_DIR / "prompts" / "system_prompt.md").read_text(encoding="utf-8")
    knowledge = (BASE_DIR / "knowledge" / "personal_master.md").read_text(encoding="utf-8")
    return prompt.replace("{knowledge}", knowledge.strip())


SYSTEM_PROMPT = build_system_prompt()

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


async def check_server(transport: httpx.AsyncBaseTransport | None = None) -> str | None:
    """Проверить доступность DeepSeek."""
    if not DEEPSEEK_API_KEY:
        return "Не задан DEEPSEEK_API_KEY. Скопируйте ключ DeepSeek в .env и перезапустите бота."
    try:
        async with httpx.AsyncClient(timeout=5, transport=transport) as http:
            headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
            resp = await http.get(f"{DEEPSEEK_BASE_URL.rstrip('/')}/models", headers=headers)
            resp.raise_for_status()
    except Exception as exc:
        return (
            f"Не удалось подключиться к DeepSeek по адресу {DEEPSEEK_BASE_URL} ({exc.__class__.__name__}). "
            "Проверьте DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL и доступ к интернету."
        )
    return None


async def ask(question: str) -> str:
    """Отправить вопрос в DeepSeek и вернуть ответ."""
    response = await _client.chat.completions.create(
        model=_MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.3,
    )
    text = response.choices[0].message.content or ""
    # Некоторые модели (qwen3, deepseek-r1) выдают рассуждения в <think>…</think> — клиенту их не показываем.
    return _THINK_RE.sub("", text).strip()
