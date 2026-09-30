import html

from aiogram import Bot
from aiogram.types import User

from bot import config

METHOD_LABELS = {"telegram": "Telegram", "email": "Email", "phone": "Телефон"}


def build_lead_message(user: User, method: str, contact: str | None = None, topic: str | None = None) -> str:
    """Текст уведомления владельцу (HTML). Данные клиента экранируются."""
    name = html.escape(user.full_name)
    username = f" (@{html.escape(user.username)})" if user.username else ""

    if method == "telegram":
        if user.username:
            contact_line = f"@{html.escape(user.username)}"
        else:
            contact_line = "юзернейма нет — откройте профиль по ссылке в имени клиента"
    else:
        contact_line = html.escape(contact or "")

    topic_line = f"Тема: {html.escape(topic)}\n" if topic else ""

    return (
        "<b>Новая заявка на связь</b>\n\n"
        f'Клиент: <a href="tg://user?id={user.id}">{name}</a>{username}\n'
        f"{topic_line}"
        f"Удобный способ связи: {METHOD_LABELS[method]}\n"
        f"Контакт: {contact_line}\n"
        f"Telegram ID: <code>{user.id}</code>"
    )


async def notify_owner(bot: Bot, text: str) -> None:
    """Отправить сообщение владельцу. Исключение при ошибке — его обрабатывает вызывающий код."""
    await bot.send_message(config.ADMIN_ID, text, parse_mode="HTML")
