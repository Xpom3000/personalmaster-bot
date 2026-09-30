import logging

from aiogram import F, Router
from aiogram.types import Message

from bot.services import ai

router = Router()

TELEGRAM_LIMIT = 4096
ERROR_TEXT = "Извините, сейчас не получилось ответить. Попробуйте, пожалуйста, чуть позже."


def _chunks(text: str, size: int = TELEGRAM_LIMIT):
    """Telegram не принимает сообщения длиннее 4096 символов — режем на части."""
    for i in range(0, len(text), size):
        yield text[i : i + size]


# Обычный текст: не пустой и не команда (/start и т.п.)
@router.message(F.text, ~F.text.startswith("/"))
async def answer_question(message: Message) -> None:
    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        answer = await ai.ask(message.text)
    except Exception:
        logging.exception("DeepSeek request failed")
        await message.answer(ERROR_TEXT)
        return

    if not answer:
        await message.answer(ERROR_TEXT)
        return

    for part in _chunks(answer):
        await message.answer(part)
