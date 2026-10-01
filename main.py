import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from bot.config import ADMIN_ID, BOT_TOKEN
from bot import catalog, db
from bot.handlers import cart, consultant, lead, menu, start
from bot.services import ai


async def main() -> None:
    if not BOT_TOKEN:
        sys.exit("Не задан BOT_TOKEN. Скопируйте .env.example в .env и вставьте токен от @BotFather.")
    if not ADMIN_ID:
        sys.exit("Не задан ADMIN_ID. Укажите в .env числовой Telegram ID владельца (узнать: @userinfobot).")

    if not catalog.CATALOG.services:
        sys.exit("В базе знаний (knowledge/personal_master.md) не найдена таблица услуг с колонками «Услуга» и «Цена».")

    db.get_db()  # создаёт файл базы и таблицы при первом запуске

    problem = await ai.check_server()
    if problem:
        sys.exit(problem)

    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(menu.router)        # кнопки меню, витрина, корзина: раньше сценария заявки и консультанта
    dp.include_router(cart.router)        # корзина и оформление заказа
    dp.include_router(lead.router)        # сценарий заявки: раньше консультанта, чтобы перехватывать ввод
    dp.include_router(consultant.router)  # последним: ловит любой обычный текст
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
