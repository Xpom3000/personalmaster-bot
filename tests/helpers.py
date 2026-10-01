"""Общий стенд для сквозных тестов: диспетчер со всеми роутерами и подменённый Telegram."""
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from bot.handlers import cart, consultant, lead, menu, start

ADMIN = 999
sent = []        # (chat_id, text, parse_mode, reply_markup)
answered = []    # тексты ответов на callback
edits = []       # обновления кнопок под сообщениями
edited_texts = []  # редактирование текста сообщений: (text, parse_mode, reply_markup)
ai_calls = []


class FakeBot(Bot):
    fail_admin = False

    async def __call__(self, method, request_timeout=None):
        name = type(method).__name__
        if name == "SendMessage":
            if self.fail_admin and method.chat_id == ADMIN:
                raise RuntimeError("Forbidden: bot can't initiate conversation")
            sent.append((method.chat_id, method.text, method.parse_mode, method.reply_markup))
        elif name == "AnswerCallbackQuery":
            answered.append(method.text)
        elif name == "EditMessageReplyMarkup":
            edits.append(method.reply_markup)
        elif name == "EditMessageText":
            edited_texts.append((method.text, method.parse_mode, method.reply_markup))
        return True


dp = Dispatcher()
dp.include_router(start.router)
dp.include_router(menu.router)
dp.include_router(cart.router)
dp.include_router(lead.router)
dp.include_router(consultant.router)
bot = FakeBot("123456:TEST")

_counter = [0]


def _update(user, *, text=None, data=None):
    _counter[0] += 1
    frm = {"id": user["id"], "is_bot": False, "first_name": user["first"]}
    if user.get("username"):
        frm["username"] = user["username"]
    chat = {"id": user["id"], "type": "private"}
    if text is not None:
        body = {"update_id": _counter[0], "message": {"message_id": _counter[0], "date": 0, "chat": chat, "from": frm, "text": text}}
        if text.startswith("/"):
            body["message"]["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
    else:
        body = {"update_id": _counter[0], "callback_query": {
            "id": str(_counter[0]), "from": frm, "chat_instance": "x", "data": data,
            "message": {"message_id": 1, "date": 0, "chat": chat, "from": {"id": 1, "is_bot": True, "first_name": "b"}, "text": "m"}}}
    return Update.model_validate(body)


def send(user, *, text=None, data=None):
    """Отправить боту сообщение или нажатие кнопки; вернуть всё, что бот отправил в ответ."""
    sent.clear(); answered.clear(); edits.clear(); edited_texts.clear(); ai_calls.clear()
    asyncio.run(dp.feed_update(bot, _update(user, text=text, data=data)))
    return list(sent)


def to_user(msgs, uid):
    return [m[1] for m in msgs if m[0] == uid]


def to_admin(msgs):
    return [m for m in msgs if m[0] == ADMIN]


def button_texts(markup):
    """Тексты всех кнопок клавиатуры (обычной или inline)."""
    rows = getattr(markup, "keyboard", None) or getattr(markup, "inline_keyboard", [])
    return [b.text for row in rows for b in row]


def button_data(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]
