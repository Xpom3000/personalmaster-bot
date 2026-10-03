import logging

from aiogram import Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot import config, db
from bot.keyboards import anons_keyboard, main_menu

router = Router()

WELCOME = (
    "Здравствуйте! Я помощник студии «Персональный мастер». "
    "Отвечу на вопросы об услугах, ценах и записи. "
    "В меню под полем ввода можно открыть витрину услуг, корзину или связаться с мастером."
)
ANONS_TEXT = (
    "Напоминаем: в витрине бота собраны все услуги студии «Персональный мастер» с ценами. "
    "Выберите услугу и оформите заказ прямо в боте."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()  # /start всегда сбрасывает незавершённую заявку
    await message.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("anons"))
async def cmd_anons(message: Message) -> None:
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("Эта команда доступна только владельцу.")
        return

    recipients = db.get_db().broadcast_users()
    sent = 0
    failed = 0
    for user_id in recipients:
        try:
            await message.bot.send_message(user_id, ANONS_TEXT, reply_markup=anons_keyboard())
            sent += 1
        except Exception as exc:
            failed += 1
            if isinstance(exc, TelegramForbiddenError):
                logging.info("Пропускаю заблокированного пользователя: %s", user_id)
            else:
                logging.exception("Не удалось отправить анонс пользователю %s", user_id)

    await message.answer(f"Разослано: {sent}\nНе удалось: {failed}")
