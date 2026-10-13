import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().strip('"').strip("'")

# Telegram ID владельца: сюда приходят заявки на связь
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip() or 0)
except ValueError:
    ADMIN_ID = 0

# air.fail API: основной провайдер для чата.
AIRFAIL_API_KEY = os.getenv("AIRFAIL_API_KEY", "").strip().strip('"').strip("'")
AIRFAIL_BASE_URL = (
    os.getenv("AIRFAIL_BASE_URL", "https://api.air.fail/public/text/dola_seed")
    .strip()
    .strip('"')
    .strip("'")
)
AIRFAIL_MODEL = (
    os.getenv("AIRFAIL_MODEL", "seed-2-1-turbo").strip().strip('"').strip("'")
)
AIRFAIL_TIMEOUT = int(os.getenv("AIRFAIL_TIMEOUT", "120").strip() or 120)

# Совместимость со старыми скриптами и переменными DeepSeek.
DEEPSEEK_API_KEY = AIRFAIL_API_KEY
DEEPSEEK_BASE_URL = AIRFAIL_BASE_URL
DEEPSEEK_MODEL = AIRFAIL_MODEL
DEEPSEEK_TIMEOUT = AIRFAIL_TIMEOUT

# Файл базы данных SQLite (корзины и заказы). Папка data/ не попадает в git.
DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", "").strip() or BASE_DIR / "data" / "bot.db"
)

# ЮKassa: тестовый режим работает с ключами магазина и секретным ключом.
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "").strip()
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "").strip()
YOOKASSA_RETURN_URL = os.getenv(
    "YOOKASSA_RETURN_URL", "https://t.me/marina_beauty_helper_bot"
).strip()
