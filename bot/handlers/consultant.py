import logging

from aiogram import F, Router
from aiogram.types import Message

from bot import guardrails
from bot.keyboards import main_menu
from bot.services import ai

router = Router()

TELEGRAM_LIMIT = 4096
ERROR_TEXT = (
    "Извините, сейчас не получилось ответить. Попробуйте, пожалуйста, чуть позже "
    "или нажмите «Связаться с человеком», и Марина ответит лично."
)

_rate_limiter = guardrails.RateLimiter()
_leak_detector = guardrails.LeakDetector(ai.SYSTEM_PROMPT)


def _chunks(text: str, size: int = TELEGRAM_LIMIT):
    """Telegram не принимает сообщения длиннее 4096 символов — режем на части."""
    for i in range(0, len(text), size):
        yield text[i : i + size]


# Обычный текст: не пустой и не команда (/start и т.п.)
@router.message(F.text, ~F.text.startswith("/"))
async def answer_question(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else message.chat.id
    text = message.text

    # 1. Ограничители на входе — до обращения к модели
    if not _rate_limiter.allow(user_id):
        await message.answer(guardrails.TOO_FAST, reply_markup=main_menu())
        return
    if len(text) > guardrails.MAX_INPUT_CHARS:
        await message.answer(guardrails.TOO_LONG, reply_markup=main_menu())
        return
    if guardrails.is_injection_attempt(text):
        logging.warning("Заблокирована попытка обхода правил: user=%s text=%r", user_id, text[:100])
        await message.answer(guardrails.REFUSAL_INJECTION, reply_markup=main_menu())
        return

    # 2. Запрос к модели (роль, тема и правила заданы системным промптом)
    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        answer = await ai.ask(text)
    except Exception:
        logging.exception("Ollama request failed")
        await message.answer(ERROR_TEXT, reply_markup=main_menu())
        return

    if not answer:
        await message.answer(ERROR_TEXT, reply_markup=main_menu())
        return

    # 3. Ограничитель на выходе — не раскрывает ли ответ служебные инструкции
    answer = guardrails.filter_output(answer, _leak_detector)

    parts = list(_chunks(answer))
    for part in parts:
        # Нижнее меню должно оставаться под полем ввода после любого ответа бота.
        await message.answer(part, reply_markup=main_menu())
