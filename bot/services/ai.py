import re

import httpx

from bot.config import (
    BASE_DIR,
    AIRFAIL_API_KEY,
    AIRFAIL_BASE_URL,
    AIRFAIL_MODEL,
    AIRFAIL_TIMEOUT,
)

USE_AIRFAIL = True
_MODEL_NAME = AIRFAIL_MODEL
_BASE_URL = AIRFAIL_BASE_URL
_TIMEOUT = AIRFAIL_TIMEOUT


def build_system_prompt() -> str:
    """Системный промпт + база знаний. Читается один раз при старте бота."""
    prompt = (BASE_DIR / "prompts" / "system_prompt.md").read_text(encoding="utf-8")
    knowledge = (BASE_DIR / "knowledge" / "personal_master.md").read_text(
        encoding="utf-8"
    )
    return prompt.replace("{knowledge}", knowledge.strip())


SYSTEM_PROMPT = build_system_prompt()

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


async def check_server(transport: httpx.AsyncBaseTransport | None = None) -> str | None:
    """Проверить доступность air.fail."""
    if not AIRFAIL_API_KEY:
        return "Не задан AIRFAIL_API_KEY. Скопируйте ключ air.fail в .env и перезапустите бота."
    try:
        async with httpx.AsyncClient(timeout=5, transport=transport, verify=False) as http:
            headers = {"Authorization": AIRFAIL_API_KEY}
            resp = await http.get(
                f"{AIRFAIL_BASE_URL.rstrip('/')}/public/text", headers=headers
            )
            resp.raise_for_status()
    except Exception as exc:
        return (
            f"Не удалось подключиться к air.fail по адресу {AIRFAIL_BASE_URL} ({exc.__class__.__name__}). "
            "Проверьте AIRFAIL_API_KEY, AIRFAIL_BASE_URL и доступ к интернету."
        )
    return None


async def ask(question: str) -> str:
    """Отправить вопрос в air.fail и вернуть ответ."""
    # air.fail принимает один текст, а не массив messages, поэтому склеиваем
    dialog_text = (
        f"[ИНСТРУКЦИИ]: {SYSTEM_PROMPT}\n\n" f"[КЛИЕНТ]: {question}\n\n" f"[АССИСТЕНТ]:"
    )

    headers = {
        "Authorization": AIRFAIL_API_KEY,  # без "Bearer"
    }
    form_data = {
        "content": dialog_text,
        "info": f'{{"version": "{_MODEL_NAME}", "temperature": 0.3}}',
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT, verify=False) as http:
        resp = await http.post(_BASE_URL, data=form_data, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    try:
        text = data[0]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""

    # Некоторые модели (qwen3, deepseek-r1) выдают рассуждения в <think>…</think> — клиенту их не показываем.
    return _THINK_RE.sub("", text).strip()
