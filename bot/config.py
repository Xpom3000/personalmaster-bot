import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Telegram ID владельца: сюда приходят заявки на связь
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip() or 0)
except ValueError:
    ADMIN_ID = 0

# DeepSeek API: основной провайдер для чата.
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", "")).strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
DEEPSEEK_TIMEOUT = float(os.getenv("DEEPSEEK_TIMEOUT", "120"))

# Файл базы данных SQLite (корзины и заказы). Папка data/ не попадает в git.
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "").strip() or BASE_DIR / "data" / "bot.db")

# ЮKassa: тестовый режим работает с ключами магазина и секретным ключом.
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "").strip()
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "").strip()
YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL", "https://example.com/payments/return").strip()
