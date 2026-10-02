import sys
import traceback
import logging
from pathlib import Path

from aiogram import BaseMiddleware, Bot, Dispatcher
from dotenv import load_dotenv
import os

# Загружаем .env из корня проекта (там, где лежит main.py)
load_dotenv(Path(__file__).resolve().parent / ".env")

# Импорты. Если какой-то модуль не найдётся — увидим понятную ошибку
try:
    from bot.config import ADMIN_ID, BOT_TOKEN
    from bot import catalog, db
    from bot.handlers import cart, consultant, lead, menu, start
    from bot.services import ai
except Exception as e:
    print("❌ ОШИБКА при импорте модулей:", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

class UserTrackingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user and not user.is_bot:
            try:
                db.get_db().register_user(user.id, user.username, user.full_name or user.first_name)
            except Exception as db_err:
                # Если БД ещё не готова — не ломаем бота, просто логируем
                logger.warning("Не удалось зарегистрировать пользователя в БД: %s", db_err)
        return await handler(event, data)

async def main() -> None:
    # 1. Проверка токена и админа
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не задан. Проверьте файл .env")
        sys.exit(1)
    if not ADMIN_ID:
        logger.warning("⚠️ ADMIN_ID не задан. Админ-функции будут недоступны.")

    # 2. Проверка каталога (если он критически важен)
    if not catalog.CATALOG.services:
        logger.warning("⚠️ В каталоге нет услуг. Бот запустится, но раздел каталога будет пустым.")

    # 3. Инициализация БД
    try:
        db.get_db()
        logger.info("✅ База данных инициализирована.")
    except Exception as db_err:
        logger.error("❌ Не удалось инициализировать БД: %s", db_err)
        sys.exit(1)

    # 4. Проверка AI-сервиса
    try:
        problem = await ai.check_server()
        if problem:
            logger.warning(f"⚠️ Проблема с AI-сервером: {problem}. Бот запустится без AI-функций.")
        else:
            logger.info("✅ AI-сервер доступен.")
    except Exception as ai_err:
        logger.warning(f"⚠️ Не удалось проверить AI-сервер: {ai_err}. Бот запустится без AI.")

    # 5. Создание бота и диспетчера
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    dp.message.middleware(UserTrackingMiddleware())
    dp.callback_query.middleware(UserTrackingMiddleware())

    # 6. Подключение всех роутеров
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(cart.router)
    dp.include_router(lead.router)
    dp.include_router(consultant.router)

    logger.info("🚀 БОТ ЗАПУСКАЕТСЯ... Ждём сообщений в Telegram!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем.")
    except Exception:
        print("\n💥 КРИТИЧЕСКАЯ ОШИБКА:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
