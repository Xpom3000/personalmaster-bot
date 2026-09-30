import re

import httpx
from openai import AsyncOpenAI

from bot.config import BASE_DIR, OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

# Ollama совместим с OpenAI SDK. Ключ не проверяется, но SDK требует непустое значение.
_client = AsyncOpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL, timeout=OLLAMA_TIMEOUT)


def build_system_prompt() -> str:
    """Системный промпт + база знаний. Читается один раз при старте бота."""
    prompt = (BASE_DIR / "prompts" / "system_prompt.md").read_text(encoding="utf-8")
    knowledge = (BASE_DIR / "knowledge" / "personal_master.md").read_text(encoding="utf-8")
    return prompt.replace("{knowledge}", knowledge.strip())


SYSTEM_PROMPT = build_system_prompt()

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


async def check_server(transport: httpx.AsyncBaseTransport | None = None) -> str | None:
    """Проверить, что Ollama запущен и нужная модель скачана.

    Возвращает None, если всё в порядке, иначе понятное описание проблемы.
    """
    root = OLLAMA_BASE_URL.rstrip("/").removesuffix("/v1")
    try:
        async with httpx.AsyncClient(timeout=5, transport=transport) as http:
            resp = await http.get(f"{root}/api/tags")
            resp.raise_for_status()
    except Exception as exc:
        return (
            f"Не удалось подключиться к Ollama по адресу {root} ({exc.__class__.__name__}). "
            "Запустите сервер (команда `ollama serve` или приложение Ollama) "
            "и проверьте OLLAMA_BASE_URL в .env."
        )
    names = {m.get("name", "") for m in resp.json().get("models", [])}
    if OLLAMA_MODEL not in names and f"{OLLAMA_MODEL}:latest" not in names:
        return f"Модель «{OLLAMA_MODEL}» не найдена в Ollama. Скачайте её: ollama pull {OLLAMA_MODEL}"
    return None


async def ask(question: str) -> str:
    """Отправить вопрос в модель Ollama (с базой знаний студии) и вернуть ответ."""
    response = await _client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.3,
    )
    text = response.choices[0].message.content or ""
    # Некоторые модели (qwen3, deepseek-r1) выдают рассуждения в <think>…</think> — клиенту их не показываем.
    return _THINK_RE.sub("", text).strip()
