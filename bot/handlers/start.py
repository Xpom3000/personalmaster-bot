from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards import main_menu

router = Router()

WELCOME = (
    "Здравствуйте! Я помощник студии «Персональный мастер». "
    "Отвечу на вопросы об услугах, ценах и записи. "
    "В меню под полем ввода можно открыть витрину услуг, корзину или связаться с мастером."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()  # /start всегда сбрасывает незавершённую заявку
    await message.answer(WELCOME, reply_markup=main_menu())
