import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN, DEEPSEEK_API_KEY
from bot.handlers import consultant, start


async def main() -> None:
    if not BOT_TOKEN:
        sys.exit("Не задан BOT_TOKEN. Скопируйте .env.example в .env и вставьте токен от @BotFather.")
    if not DEEPSEEK_API_KEY:
        sys.exit("Не задан DEEPSEEK_API_KEY. Добавьте ключ DeepSeek в файл .env.")

    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(consultant.router)  # после start: ловит любой обычный текст
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
