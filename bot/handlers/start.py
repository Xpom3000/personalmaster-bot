from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()

WELCOME = (
    "Здравствуйте! Я помощник студии «Персональный мастер» 💅\n"
    "Скоро смогу рассказать об услугах и помочь записаться."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME)
