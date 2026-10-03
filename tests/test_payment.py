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


# ---------- попытка подтвердить неоплаченный заказ ----------

def _order_with_payment(uid):
    """Заказ «ожидает оплаты» со ссылкой на оплату (платёж создан, но клиент ещё не заплатил)."""
    u = user(uid)
    send(u, data=f"cart:add:{GEL.id}")
    send(u, data="order:create")
    order_id = 1  # в чистой базе теста это первый заказ
    db.get_db().set_order_payment(order_id, "pay_123", "https://example.com/pay/123")
    return u, order_id


def _paid_at(order_id):
    return db.get_db()._conn.execute("SELECT paid_at FROM orders WHERE id = ?", (order_id,)).fetchone()[0]


@pytest.fixture
def owner_notices(monkeypatch):
    notices = []

    async def fake_notify(bot, text):
        notices.append(text)

    monkeypatch.setattr(cart, "notify_owner", fake_notify)
    return notices


@pytest.mark.parametrize("status,alert", [
    ("pending", "Платёж ещё не завершён"),
    ("waiting_for_capture", "Платёж получен, подтверждаем"),
    ("canceled", "Платёж отменён"),
])
def test_unpaid_order_is_not_confirmed(monkeypatch, owner_notices, status, alert):
    u, order_id = _order_with_payment(110)

    async def fake_status(payment_id):
        return status

    monkeypatch.setattr(yookassa, "check_payment_status", fake_status)
    send(u, data=f"order:paid:{order_id}")

    assert alert in helpers.answered[0]                      # клиент видит, что оплата не подтверждена
    order = db.get_db().get_order(order_id)
    assert order.status == "ожидает оплаты" and _paid_at(order_id) is None
    assert owner_notices == []                               # владельцу сообщение об оплате не уходит


def test_confirm_without_payment_link(monkeypatch, owner_notices):
    u = user(111)
    send(u, data=f"cart:add:{GEL.id}")
    send(u, data="order:create")                             # платёж ещё не создавался

    async def must_not_be_called(payment_id):
        raise AssertionError("статус не должен запрашиваться без платежа")

    monkeypatch.setattr(yookassa, "check_payment_status", must_not_be_called)
    send(u, data="order:paid:1")

    assert "Сначала откройте ссылку на оплату" in helpers.answered[0]
    assert db.get_db().get_order(1).status == "ожидает оплаты" and owner_notices == []


def test_yookassa_error_does_not_mark_order_paid(monkeypatch, owner_notices):
    u, order_id = _order_with_payment(112)

    async def broken_status(payment_id):
        raise RuntimeError("ЮKassa недоступна")

    monkeypatch.setattr(yookassa, "check_payment_status", broken_status)
    send(u, data=f"order:paid:{order_id}")

    assert helpers.answered == [cart.PAYMENT_CHECK_FAILED]
    assert db.get_db().get_order(order_id).status == "ожидает оплаты" and owner_notices == []


def test_paid_after_unpaid_attempt(monkeypatch, owner_notices):
    """Сначала платёж не завершён, потом клиент платит и подтверждает ещё раз — заказ оплачен."""
    u, order_id = _order_with_payment(113)
    statuses = iter(["pending", "succeeded"])

    async def fake_status(payment_id):
        return next(statuses)

    monkeypatch.setattr(yookassa, "check_payment_status", fake_status)
    send(u, data=f"order:paid:{order_id}")
    assert db.get_db().get_order(order_id).status == "ожидает оплаты"

    send(u, data=f"order:paid:{order_id}")
    assert db.get_db().get_order(order_id).status == "оплачен" and _paid_at(order_id) is not None
    assert len(owner_notices) == 1


def test_repeated_confirmation_of_paid_order(monkeypatch, owner_notices):
    u, order_id = _order_with_payment(114)

    async def succeeded(payment_id):
        return "succeeded"

    monkeypatch.setattr(yookassa, "check_payment_status", succeeded)
    send(u, data=f"order:paid:{order_id}")
    send(u, data=f"order:paid:{order_id}")                   # двойное нажатие «Я оплатил»

    assert "уже оплачен" in helpers.answered[0]
    assert len(owner_notices) == 1                           # владельцу сообщение пришло один раз
