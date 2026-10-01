import pytest

from bot import catalog, db
from bot.handlers import cart
from bot.services import yookassa
from tests import helpers
from tests.helpers import button_texts, send

pytestmark = pytest.mark.usefixtures("stand")

SVC = catalog.CATALOG.services
GEL = SVC[0]


def user(uid):
    return {"id": uid, "first": "Анна", "username": "anna"}


def test_checkout_shows_pay_button_for_pending_order():
    u = user(101)
    send(u, data=f"cart:add:{GEL.id}")
    send(u, data="order:create")

    order = db.get_db().get_order(1)
    assert order.status == "ожидает оплаты"
    _, _, markup = helpers.edited_texts[-1]
    assert button_texts(markup) == ["Оплатить"]


def test_payment_callback_creates_yookassa_payment_and_keeps_link(monkeypatch):
    u = user(102)
    send(u, data=f"cart:add:{GEL.id}")
    send(u, data="order:create")

    async def fake_create_payment(order):
        return "pay_123", "https://example.com/pay/123"

    monkeypatch.setattr(yookassa, "create_payment_for_order", fake_create_payment)
    send(u, data="order:pay:1")

    order = db.get_db().get_order(1)
    assert order.payment_id == "pay_123"
    assert order.payment_url == "https://example.com/pay/123"
    _, _, markup = helpers.edited_texts[-1]
    assert button_texts(markup) == ["Оплатить заказ", "Я оплатил"]


def test_paid_order_is_marked_paid_and_admin_gets_notification(monkeypatch):
    u = user(103)
    send(u, data=f"cart:add:{GEL.id}")
    send(u, data="order:create")
    db.get_db().set_order_payment(1, "pay_123", "https://example.com/pay/123")

    async def fake_check_payment_status(payment_id):
        assert payment_id == "pay_123"
        return "succeeded"

    monkeypatch.setattr(yookassa, "check_payment_status", fake_check_payment_status)

    notified = []

    async def fake_notify(bot, text):
        notified.append(text)

    monkeypatch.setattr(cart, "notify_owner", fake_notify)
    send(u, data="order:paid:1")

    order = db.get_db().get_order(1)
    assert order.status == "оплачен"
    assert notified and "Новый оплаченный заказ" in notified[0]
