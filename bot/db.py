"""База данных SQLite: корзины и заказы.

Обращения синхронные: запросы к локальному файлу занимают доли миллисекунды,
а бот обслуживает единицы клиентов в секунду. Все операции выполняются из потока
event loop, поэтому один общий connection безопасен.
"""
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from bot import config
from bot.catalog import Service

STATUS_PENDING = "ожидает оплаты"
STATUS_PAID = "оплачен"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bot_users (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT,
    first_name TEXT,
    last_seen  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cart_items (
    user_id    INTEGER NOT NULL,
    service_id TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    PRIMARY KEY (user_id, service_id)          -- одна услуга не может лежать в корзине дважды
);
CREATE TABLE IF NOT EXISTS orders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    username     TEXT,
    full_name    TEXT    NOT NULL,
    status       TEXT    NOT NULL,
    total        INTEGER NOT NULL,             -- сумма позиций с фиксированной ценой, ₽
    has_variable INTEGER NOT NULL DEFAULT 0,   -- 1, если есть позиции без фиксированной цены
    payment_id   TEXT,
    payment_url  TEXT,
    paid_at      TEXT,
    created_at   TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS order_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    service_id TEXT    NOT NULL,
    name       TEXT    NOT NULL,               -- название и цена сохраняются на момент заказа
    price_text TEXT    NOT NULL,
    amount     INTEGER                         -- NULL для цены без фиксированной суммы
);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
"""


@dataclass(frozen=True)
class OrderLine:
    service_id: str
    name: str
    price_text: str
    amount: int | None


@dataclass(frozen=True)
class Order:
    id: int
    status: str
    total: int
    has_variable: bool
    lines: list[OrderLine]
    payment_id: str | None = None
    payment_url: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._ensure_columns()
        self._conn.commit()

    def _ensure_columns(self) -> None:
        """Добавляет отсутствующие колонки для оплаты в старых базах."""
        columns = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(orders)").fetchall()
        }
        for name, ddl in {
            "payment_id": "ALTER TABLE orders ADD COLUMN payment_id TEXT",
            "payment_url": "ALTER TABLE orders ADD COLUMN payment_url TEXT",
            "paid_at": "ALTER TABLE orders ADD COLUMN paid_at TEXT",
        }.items():
            if name not in columns:
                self._conn.execute(ddl)

    # --- корзина ---

    def add_to_cart(self, user_id: int, service_id: str) -> bool:
        """True, если услуга добавлена; False, если она уже лежала в корзине."""
        with self._conn:
            cur = self._conn.execute(
                "INSERT OR IGNORE INTO cart_items (user_id, service_id, created_at) VALUES (?, ?, ?)",
                (user_id, service_id, _now()),
            )
        return cur.rowcount == 1

    def remove_from_cart(self, user_id: int, service_id: str) -> bool:
        """True, если услуга убрана; False, если её уже не было (двойное нажатие)."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM cart_items WHERE user_id = ? AND service_id = ?",
                (user_id, service_id),
            )
        return cur.rowcount == 1

    def cart_service_ids(self, user_id: int) -> list[str]:
        rows = self._conn.execute(
            "SELECT service_id FROM cart_items WHERE user_id = ? ORDER BY rowid", (user_id,)
        ).fetchall()
        return [r["service_id"] for r in rows]

    def in_cart(self, user_id: int, service_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM cart_items WHERE user_id = ? AND service_id = ?", (user_id, service_id)
        ).fetchone()
        return row is not None

    # --- заказы ---

    def create_order_from_cart(
        self,
        user_id: int,
        username: str | None,
        full_name: str,
        resolve: Callable[[str], Service | None],
    ) -> Order | None:
        """Одной транзакцией: собрать заказ из корзины и очистить корзину.

        `resolve` превращает id услуги в актуальную услугу каталога; услуги, которых
        больше нет или у которых нет цены, в заказ не попадают. Возвращает None,
        если оформлять нечего (корзина пуста), — заказ при этом не создаётся.
        """
        with self._conn:
            ids = self.cart_service_ids(user_id)
            services = [s for sid in ids if (s := resolve(sid)) and s.has_price]
            self._conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
            if not services:
                return None

            lines = [OrderLine(s.id, s.name, s.price, s.amount) for s in services]
            total = sum(l.amount for l in lines if l.amount is not None)
            has_variable = any(l.amount is None for l in lines)
            cur = self._conn.execute(
                "INSERT INTO orders (user_id, username, full_name, status, total, has_variable, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, username, full_name, STATUS_PENDING, total, int(has_variable), _now()),
            )
            order_id = cur.lastrowid
            self._conn.executemany(
                "INSERT INTO order_items (order_id, service_id, name, price_text, amount) VALUES (?, ?, ?, ?, ?)",
                [(order_id, l.service_id, l.name, l.price_text, l.amount) for l in lines],
            )
        return Order(order_id, STATUS_PENDING, total, has_variable, lines)

    def get_order(self, order_id: int) -> Order | None:
        row = self._conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            return None
        items = self._conn.execute(
            "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
        ).fetchall()
        lines = [OrderLine(i["service_id"], i["name"], i["price_text"], i["amount"]) for i in items]
        return Order(
            row["id"],
            row["status"],
            row["total"],
            bool(row["has_variable"]),
            lines,
            row["payment_id"],
            row["payment_url"],
        )

    def set_order_payment(self, order_id: int, payment_id: str, payment_url: str) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "UPDATE orders SET payment_id = ?, payment_url = ? WHERE id = ?",
                (payment_id, payment_url, order_id),
            )
        return cur.rowcount == 1

    def mark_order_paid(self, order_id: int) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "UPDATE orders SET status = ?, paid_at = ? WHERE id = ? AND status != ?",
                (STATUS_PAID, _now(), order_id, STATUS_PAID),
            )
        return cur.rowcount == 1

    def orders_count(self, user_id: int) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (user_id,)).fetchone()[0]

    def register_user(self, user_id: int, username: str | None, first_name: str | None) -> None:
        """Запомнить пользователя, который когда-либо писал боту."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO bot_users (user_id, username, first_name, last_seen)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_seen = excluded.last_seen
                """,
                (user_id, username, first_name, _now()),
            )

    def broadcast_users(self) -> list[int]:
        """Список пользователей, кому можно отправлять анонс."""
        rows = self._conn.execute(
            "SELECT user_id FROM bot_users ORDER BY user_id"
        ).fetchall()
        return [row["user_id"] for row in rows]


_db: Database | None = None


def get_db() -> Database:
    """Общая база бота; создаётся при первом обращении (файл и таблицы — автоматически)."""
    global _db
    if _db is None:
        _db = Database(config.DATABASE_PATH)
    return _db


def set_db(database: Database | None) -> None:
    """Подмена базы (для тестов)."""
    global _db
    _db = database
