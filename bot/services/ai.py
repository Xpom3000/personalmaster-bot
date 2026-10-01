import re

import httpx
from openai import AsyncOpenAI

from bot.config import (
    BASE_DIR,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
)

USE_DEEPSEEK = bool(DEEPSEEK_API_KEY)
_MODEL_NAME = DEEPSEEK_MODEL if USE_DEEPSEEK else OLLAMA_MODEL
_BASE_URL = DEEPSEEK_BASE_URL if USE_DEEPSEEK else OLLAMA_BASE_URL
_TIMEOUT = DEEPSEEK_TIMEOUT if USE_DEEPSEEK else OLLAMA_TIMEOUT

# OpenAI-совместимый клиент: для DeepSeek нужен реальный API-ключ, для Ollama — любой строковый "ключ".
_client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY or "ollama", base_url=_BASE_URL, timeout=_TIMEOUT)


def build_system_prompt() -> str:
    """Системный промпт + база знаний. Читается один раз при старте бота."""
    prompt = (BASE_DIR / "prompts" / "system_prompt.md").read_text(encoding="utf-8")
    knowledge = (BASE_DIR / "knowledge" / "personal_master.md").read_text(encoding="utf-8")
    return prompt.replace("{knowledge}", knowledge.strip())


SYSTEM_PROMPT = build_system_prompt()

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


async def check_server(transport: httpx.AsyncBaseTransport | None = None) -> str | None:
    """Проверить доступность модели. При DeepSeek проверяем только API-ключ и соединение."""
    if USE_DEEPSEEK:
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
