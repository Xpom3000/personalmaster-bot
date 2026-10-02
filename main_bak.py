#import asyncio
import logging
import sys

from aiohttp import web
from aiogram import BaseMiddleware, Bot, Dispatcher

from bot.config import ADMIN_ID, BOT_TOKEN
from bot import catalog, db
from bot.handlers import cart, consultant, lead, menu, start
#from bot.handlers.webhook import yookassa_webhook
from bot.services import ai


class UserTrackingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user and not user.is_bot:
            db.get_db().register_user(user.id, user.username, user.full_name or user.first_name)
        return await handler(event, data)


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
    dp.message.middleware(UserTrackingMiddleware())
    dp.callback_query.middleware(UserTrackingMiddleware())
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(cart.router)
    dp.include_router(lead.router)
    dp.include_router(consultant.router)

    # aiohttp-сервер для вебхуков YooKassa
    # app = web.Application()
    # app["bot"] = bot
    # app.router.add_post("/yookassa/webhook", yookassa_webhook)
    # runner = web.AppRunner(app)
    # await runner.setup()
    # site = web.TCPSite(runner, host="0.0.0.0", port=8080)
    # await site.start()
    # logging.info("Вебхук-сервер запущен на http://0.0.0.0:8080/yookassa/webhook")
    await dp.start_polling(bot)