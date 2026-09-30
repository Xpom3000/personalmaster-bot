import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN
from bot.handlers import consultant, start
from bot.services import ai


async def main() -> None:
    if not BOT_TOKEN:
        sys.exit("Не задан BOT_TOKEN. Скопируйте .env.example в .env и вставьте токен от @BotFather.")

    problem = await ai.check_server()
    if problem:
        sys.exit(problem)

    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(consultant.router)  # после start: ловит любой обычный текст
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
