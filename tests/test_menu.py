import pytest

from bot import catalog, db
from bot.catalog import Catalog, parse_services
from bot.handlers import menu
from tests import helpers
from tests.helpers import ADMIN, button_data, button_texts, send, to_admin, to_user

pytestmark = pytest.mark.usefixtures("stand")

MENU = ["🛍 Витрина", "🧺 Корзина", "💬 Связаться с мастером"]


def _cards(msgs, uid):
    return [m for m in msgs if m[0] == uid and m[2] == "HTML"]


def test_start_shows_persistent_menu():
    u = {"id": 101, "first": "Анна"}
    m = send(u, text="/start")
    assert "Здравствуйте" in to_user(m, 101)[0]
    markup = m[0][3]
    assert button_texts(markup) == MENU and markup.is_persistent


def test_showcase_shows_cards_from_knowledge_base():
    u = {"id": 102, "first": "Анна"}
    m = send(u, text="Витрина")
    cards = _cards(m, 102)
    assert len(cards) == len(catalog.CATALOG.services) == 7
    first_text, first_markup = cards[0][1], cards[0][3]
    assert "<b>Маникюр с покрытием гель-лаком</b>" in first_text
    assert "Уход за ногтями" in first_text and "Цена: 1 800 ₽" in first_text
    for card in cards:
        assert button_texts(card[3]) == ["Добавить в корзину"]
        assert button_data(card[3])[0].startswith("cart:add:")
    assert "Цена: 300 ₽ за два ногтя" in cards[3][1]


def test_double_add_to_cart_does_not_duplicate():
    u = {"id": 103, "first": "Анна"}
    service = catalog.CATALOG.services[0]
    m = send(u, text="Витрина")
    data = button_data(_cards(m, 103)[0][3])[0]

    send(u, data=data)
    assert helpers.answered == [menu.ADDED.format(name=service.name)]
    assert button_texts(helpers.edits[0]) == ["✓ В корзине"]
    assert db.get_db().cart_service_ids(103) == [service.id]

    send(u, data=data)                                   # двойное нажатие
    assert helpers.answered == ["Эта услуга уже в корзине"] and not helpers.edits
    send(u, data=f"cart:in:{service.id}")                # нажатие на «✓ В корзине»
    assert helpers.answered == ["Эта услуга уже в корзине"]
    assert db.get_db().cart_service_ids(103) == [service.id]

    m = send(u, text="Витрина")                           # новая витрина показывает актуальное состояние
    assert button_texts(_cards(m, 103)[0][3]) == ["✓ В корзине"]
    assert button_texts(_cards(m, 103)[1][3]) == ["Добавить в корзину"]


def test_cart_is_separate_per_user():
    service = catalog.CATALOG.services[0]
    send({"id": 104, "first": "А"}, data=f"cart:add:{service.id}")
    send({"id": 105, "first": "Б"}, data=f"cart:add:{service.id}")
    assert db.get_db().cart_service_ids(104) == db.get_db().cart_service_ids(105) == [service.id]
    assert helpers.answered == [menu.ADDED.format(name=service.name)]


def test_unknown_service_button():
    m = send({"id": 107, "first": "Анна"}, data="cart:add:deadbeef")
    assert helpers.answered == [menu.UNAVAILABLE] and not m


@pytest.fixture
def catalog_with_gaps(monkeypatch):
    md = "| Услуга | Описание | Цена |\n|---|---|---|\n| Стрижка | Быстро | 500 ₽ |\n| Особый уход | Индивидуально |  |\n| <b>Хитрая</b> | <i>тег</i> | 100 ₽ |\n"
    monkeypatch.setattr(catalog, "CATALOG", Catalog(parse_services(md)))
    return catalog.CATALOG


def test_service_without_price(catalog_with_gaps):
    u = {"id": 108, "first": "Анна", "username": "anna"}
    m = send(u, text="Витрина")
    cards = _cards(m, 108)
    no_price = cards[1]
    assert "Цена: уточняйте у мастера" in no_price[1]
    assert button_texts(no_price[3]) == ["Уточнить стоимость"]      # добавить в корзину нельзя
    assert button_data(no_price[3])[0].startswith("ask:")

    # прямое обращение к «добавить» для такой услуги отклоняется
    send(u, data=f"cart:add:{catalog_with_gaps_id(catalog_with_gaps, 'Особый уход')}")
    assert helpers.answered == [menu.UNAVAILABLE] and db.get_db().cart_service_ids(108) == []

    # «Уточнить стоимость» запускает заявку с темой для владельца
    m = send(u, data=button_data(no_price[3])[0])
    assert "Как вам удобнее связаться" in to_user(m, 108)[0]
    m = send(u, data="lead:telegram")
    admin = to_admin(m)[0][1]
    assert "Тема: уточнить стоимость услуги «Особый уход»" in admin and "@anna" in admin
    assert "заявка принята" in to_user(m, 108)[0]


def catalog_with_gaps_id(cat, name):
    return next(s.id for s in cat.services if s.name == name)


def test_html_in_knowledge_base_is_escaped(catalog_with_gaps):
    m = send({"id": 109, "first": "Анна"}, text="Витрина")
    text = _cards(m, 109)[2][1]
    assert "<b>Хитрая</b>" not in text and "&lt;b&gt;Хитрая&lt;/b&gt;" in text


def test_empty_catalog(monkeypatch):
    monkeypatch.setattr(catalog, "CATALOG", Catalog([]))
    m = send({"id": 110, "first": "Анна"}, text="Витрина")
    assert "Витрина временно недоступна" in to_user(m, 110)[0] and not _cards(m, 110)


def test_menu_button_interrupts_lead_flow():
    u = {"id": 111, "first": "Анна"}
    send(u, text="Связаться с мастером"); send(u, data="lead:email")
    send(u, text="Витрина")                               # меню доступно всегда и сбрасывает заявку
    m = send(u, text="a@b.com")
    assert helpers.ai_calls == ["a@b.com"] and not to_admin(m)


def test_contact_button_from_menu_still_works():
    u = {"id": 112, "first": "Анна", "username": "anna"}
    m = send(u, text="Связаться с мастером")
    assert "Как вам удобнее связаться" in to_user(m, 112)[0]
    m = send(u, data="lead:telegram")
    assert "Telegram" in to_admin(m)[0][1] and "Тема:" not in to_admin(m)[0][1]


def test_free_dialogue_with_ai_still_works_and_keeps_menu():
    u = {"id": 113, "first": "Анна"}
    m = send(u, text="Сколько стоит ламинирование бровей?")
    assert helpers.ai_calls == ["Сколько стоит ламинирование бровей?"]
    assert to_user(m, 113) == ["ответ модели"]
    assert button_texts(m[-1][3]) == MENU


def test_rate_limited_response_keeps_main_menu(monkeypatch):
    from bot.handlers import consultant
    from bot import guardrails

    monkeypatch.setattr(consultant, "_rate_limiter", guardrails.RateLimiter(limit=1, window=3600))
    u = {"id": 114, "first": "Анна"}

    send(u, text="Сколько стоит маникюр?")
    m = send(u, text="Сколько стоит маникюр ещё раз?")

    assert "слишком часто" in to_user(m, 114)[0].lower()
    assert button_texts(m[-1][3]) == MENU
