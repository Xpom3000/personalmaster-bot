"""Корзина и оформление заказа: экран корзины, «Убрать», «Оформить заказ», граничные случаи."""
import pytest

from bot import catalog, db
from bot.catalog import Catalog, Service
from bot.handlers import cart as cart_handler
from tests import helpers
from tests.helpers import button_data, button_texts, send

pytestmark = pytest.mark.usefixtures("stand")

SVC = catalog.CATALOG.services
GEL, PEDI, EXT, DESIGN, BROWS, LAMINATION, CERT = SVC   # порядок услуг в базе знаний
MENU = ["🛍 Витрина", "🧺 Корзина", "💬 Связаться с человеком"]


def user(uid):
    return {"id": uid, "first": "Анна", "username": "anna"}


def add(u, *services):
    for s in services:
        send(u, data=f"cart:add:{s.id}")


def open_cart(u):
    """Нажать «Корзина», вернуть (текст, кнопки) сообщения с корзиной."""
    m = send(u, text="Корзина")
    return m[0][1], m[0][3]


def cart_ids(uid):
    return db.get_db().cart_service_ids(uid)


def edited():
    return helpers.edited_texts[-1]


# ---------- экран корзины ----------

def test_empty_cart_is_polite_and_points_to_showcase():
    text, markup = open_cart(user(1))
    assert text == cart_handler.EMPTY_CART and "Витрин" in text
    assert button_texts(markup) == MENU           # инлайн-кнопок нет, остаётся обычное меню


def test_cart_lists_services_with_prices_total_and_buttons():
    u = user(2)
    add(u, GEL, PEDI)
    text, markup = open_cart(u)
    assert "<b>Ваша корзина</b>" in text
    assert "1. Маникюр с покрытием гель-лаком — 1 800 ₽" in text
    assert "2. Маникюр и педикюр — 3 200 ₽" in text
    assert "<b>Итого: 5 000 ₽</b>" in text and "*" not in text
    texts = button_texts(markup)
    assert texts[0].startswith("Убрать 1.") and texts[1].startswith("Убрать 2.") and texts[-1] == "Оформить заказ"
    assert button_data(markup) == [f"cart:rm:{GEL.id}", f"cart:rm:{PEDI.id}", "order:create"]


def test_service_added_twice_is_one_position():
    u = user(3)
    add(u, GEL, GEL, GEL)
    assert cart_ids(3) == [GEL.id]
    text, _ = open_cart(u)
    assert text.count("Маникюр с покрытием гель-лаком") == 1 and "<b>Итого: 1 800 ₽</b>" in text


def test_carts_of_different_users_are_separate():
    add(user(4), GEL)
    add(user(5), PEDI)
    assert cart_ids(4) == [GEL.id] and cart_ids(5) == [PEDI.id]
    assert "Маникюр и педикюр" not in open_cart(user(4))[0]


# ---------- «Убрать» ----------

def test_remove_recalculates_total():
    u = user(6)
    add(u, GEL, PEDI)
    send(u, data=f"cart:rm:{GEL.id}")
    assert helpers.answered == [cart_handler.REMOVED]
    text, parse_mode, markup = edited()
    assert parse_mode == "HTML" and "Маникюр с покрытием" not in text
    assert "1. Маникюр и педикюр — 3 200 ₽" in text and "<b>Итого: 3 200 ₽</b>" in text
    assert button_data(markup) == [f"cart:rm:{PEDI.id}", "order:create"]
    assert cart_ids(6) == [PEDI.id]


def test_double_remove_is_harmless():
    u = user(7)
    add(u, GEL, PEDI)
    send(u, data=f"cart:rm:{GEL.id}")
    send(u, data=f"cart:rm:{GEL.id}")                      # второе нажатие на ту же кнопку
    assert helpers.answered == [cart_handler.ALREADY_REMOVED]
    assert cart_ids(7) == [PEDI.id]                        # вторая услуга на месте
    assert "<b>Итого: 3 200 ₽</b>" in edited()[0]          # сообщение показывает актуальное состояние


def test_remove_last_item_shows_empty_cart():
    u = user(8)
    add(u, GEL)
    send(u, data=f"cart:rm:{GEL.id}")
    text, _, markup = edited()
    assert text == cart_handler.EMPTY_CART and markup is None and cart_ids(8) == []


# ---------- «Оформить заказ» ----------

def test_checkout_creates_order_and_clears_cart():
    u = user(9)
    add(u, GEL, PEDI)
    send(u, data="order:create")
    assert helpers.answered == [None]                      # уведомление закрыто без текста

    order = db.get_db().get_order(1)
    assert order.status == "ожидает оплаты" and order.total == 5000 and not order.has_variable
    assert [(l.name, l.price_text, l.amount) for l in order.lines] == [
        ("Маникюр с покрытием гель-лаком", "1 800 ₽", 1800),
        ("Маникюр и педикюр", "3 200 ₽", 3200),
    ]
    assert cart_ids(9) == [] and db.get_db().orders_count(9) == 1

    text, _, markup = edited()                             # клиент видит состав, сумму и статус
    assert "Заказ № 1 оформлен" in text and "Статус: ожидает оплаты" in text
    assert "1. Маникюр с покрытием гель-лаком — 1 800 ₽" in text and "<b>Итого: 5 000 ₽</b>" in text
    assert "Оплатить" in button_texts(markup)


def test_checkout_with_empty_cart():
    u = user(10)
    send(u, data="order:create")
    assert helpers.answered == [cart_handler.CART_EMPTY_ALERT]
    assert db.get_db().orders_count(10) == 0               # пустой заказ не создаётся
    assert edited()[0] == cart_handler.EMPTY_CART


def test_double_checkout_creates_one_order():
    u = user(11)
    add(u, GEL)
    send(u, data="order:create")
    send(u, data="order:create")                           # двойное нажатие
    assert helpers.answered == [cart_handler.CART_EMPTY_ALERT]
    assert db.get_db().orders_count(11) == 1


def test_orders_are_per_user_and_numbered():
    add(user(12), GEL); add(user(13), PEDI)
    send(user(12), data="order:create")
    assert cart_ids(13) == [PEDI.id]                       # чужая корзина не тронута
    send(user(13), data="order:create")
    assert "Заказ № 2 оформлен" in edited()[0]


def test_new_order_after_checkout():
    u = user(14)
    add(u, GEL); send(u, data="order:create")
    add(u, BROWS); send(u, data="order:create")
    assert db.get_db().orders_count(14) == 2
    assert [l.name for l in db.get_db().get_order(2).lines] == ["Коррекция и окрашивание бровей"]


# ---------- цены без фиксированной суммы ----------

def test_variable_prices_are_marked_and_excluded_from_total():
    u = user(15)
    add(u, GEL, DESIGN, CERT)
    text, _ = open_cart(u)
    assert "2. Дизайн ногтей — 300 ₽ за два ногтя *" in text
    assert "3. Подарочный сертификат — 3 000 ₽ или 5 000 ₽ *" in text
    assert "<b>Итого: 1 800 ₽</b> (без учёта позиций, отмеченных *)" in text
    assert cart_handler.VARIABLE_NOTE in text

    send(u, data="order:create")
    order = db.get_db().get_order(1)
    assert order.total == 1800 and order.has_variable
    assert [l.amount for l in order.lines] == [1800, None, None]
    assert cart_handler.VARIABLE_NOTE in edited()[0]


def test_only_variable_prices():
    u = user(16)
    add(u, CERT)
    text, _ = open_cart(u)
    assert "<b>Итого: сумму определит мастер</b>" in text
    send(u, data="order:create")
    assert db.get_db().get_order(1).total == 0


# ---------- каталог меняется, пока услуга лежит в корзине ----------

def test_service_removed_from_knowledge_base(monkeypatch):
    u = user(17)
    add(u, GEL, PEDI)
    monkeypatch.setattr(catalog, "CATALOG", Catalog([s for s in SVC if s.id != GEL.id]))
    text, _ = open_cart(u)
    assert "Маникюр с покрытием" not in text and "1. Маникюр и педикюр" in text
    assert cart_handler.DROPPED_NOTE in text and cart_ids(17) == [PEDI.id]


def test_order_keeps_prices_from_the_moment_of_checkout(monkeypatch):
    u = user(18)
    add(u, GEL)
    send(u, data="order:create")
    cheaper = Service(GEL.id, GEL.name, GEL.description, "900 ₽")
    monkeypatch.setattr(catalog, "CATALOG", Catalog([cheaper]))
    assert db.get_db().get_order(1).lines[0].price_text == "1 800 ₽"


def test_html_in_service_name_is_escaped(monkeypatch):
    evil = Service("abc12345", "<b>Хитрая</b>", "", "100 ₽")
    monkeypatch.setattr(catalog, "CATALOG", Catalog([evil]))
    u = user(19)
    send(u, data="cart:add:abc12345")
    text, _ = open_cart(u)
    assert "<b>Хитрая</b>" not in text and "&lt;b&gt;Хитрая&lt;/b&gt;" in text


# ---------- сохранность данных ----------

def test_cart_and_orders_survive_restart(tmp_path):
    path = tmp_path / "data" / "bot.db"
    first = db.Database(path)
    first.add_to_cart(20, GEL.id)
    first.add_to_cart(20, PEDI.id)
    first.create_order_from_cart(21, "u", "Пользователь", catalog.CATALOG.get)   # пустая корзина: заказа нет
    first.create_order_from_cart(20, "anna", "Анна", catalog.CATALOG.get)
    first.add_to_cart(20, BROWS.id)

    second = db.Database(path)                                # «перезапуск бота»: новый объект на тот же файл
    assert second.cart_service_ids(20) == [BROWS.id]
    assert second.get_order(1).total == 5000 and second.orders_count(20) == 1
