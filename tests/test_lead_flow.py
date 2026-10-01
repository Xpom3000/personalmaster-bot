import asyncio

import pytest
from aiogram.types import Update

from tests import helpers
from tests.helpers import ADMIN, send, to_admin, to_user

pytestmark = pytest.mark.usefixtures("stand")

_ai_calls = helpers.ai_calls
sent = helpers.sent
answered = helpers.answered
_bot = helpers.bot
_dp = helpers.dp


def test_email_flow_with_retry():
    u = {"id": 1, "first": "Анна", "username": "anna_k"}
    m = send(u, text="Связаться с мастером")
    assert "Как вам удобнее связаться" in to_user(m, 1)[0]
    m = send(u, data="lead:email")
    assert "email" in to_user(m, 1)[0]
    m = send(u, text="не email")                       # неверный формат
    assert "Не удалось распознать email" in to_user(m, 1)[0] and not to_admin(m)
    m = send(u, text="anna@example.com")
    admin = to_admin(m)
    assert len(admin) == 1
    txt = admin[0][1]
    assert "Анна" in txt and "@anna_k" in txt and "Email" in txt and "anna@example.com" in txt
    assert admin[0][2] == "HTML"
    assert "заявка принята" in to_user(m, 1)[0]
    assert not _ai_calls


def test_phone_flow_normalizes():
    u = {"id": 2, "first": "Ольга", "username": "olga"}
    send(u, text="Связаться с мастером"); send(u, data="lead:phone")
    m = send(u, text="абв")
    assert "Не удалось распознать номер" in to_user(m, 2)[0]
    m = send(u, text="8 (900) 123-45-67")
    assert "+79001234567" in to_admin(m)[0][1] and "Телефон" in to_admin(m)[0][1]


def test_telegram_flow_with_and_without_username():
    u = {"id": 3, "first": "Мария", "username": "maria"}
    send(u, text="Связаться с мастером")
    m = send(u, data="lead:telegram")
    assert "Telegram" in to_admin(m)[0][1] and "@maria" in to_admin(m)[0][1]
    assert "заявка принята" in to_user(m, 3)[0]

    u2 = {"id": 4, "first": "Без Ника"}
    send(u2, text="Связаться с мастером")
    m = send(u2, data="lead:telegram")
    txt = to_admin(m)[0][1]
    assert "tg://user?id=4" in txt and "юзернейма нет" in txt


def test_html_in_name_is_escaped():
    u = {"id": 5, "first": "<b>Хакер</b>", "username": "h"}
    send(u, text="Связаться с мастером")
    m = send(u, data="lead:telegram")
    txt = to_admin(m)[0][1]
    assert "<b>Хакер</b>" not in txt and "&lt;b&gt;Хакер&lt;/b&gt;" in txt


def test_cancel_by_text_and_button():
    u = {"id": 6, "first": "Ира"}
    send(u, text="Связаться с мастером"); send(u, data="lead:email")
    m = send(u, text="Передумала!")
    assert "заявка отменена" in to_user(m, 6)[0] and not to_admin(m)
    m = send(u, text="a@b.com")                        # состояние сброшено — уходит консультанту
    assert _ai_calls == ["a@b.com"] and not to_admin(m)

    send(u, text="Связаться с мастером")
    m = send(u, data="lead:cancel")
    assert "заявка отменена" in to_user(m, 6)[0] and not to_admin(m)


def test_free_text_on_method_step_does_not_reach_ai():
    u = {"id": 7, "first": "Света"}
    send(u, text="Связаться с мастером")
    m = send(u, text="сколько стоит маникюр?")
    assert "выберите способ связи" in to_user(m, 7)[0].lower() and not _ai_calls


def test_stale_button_and_start_reset():
    u = {"id": 8, "first": "Лена"}
    send(u, data="lead:email")                         # состояния нет
    assert answered and "неактуальна" in answered[0]

    send(u, text="Связаться с мастером"); send(u, data="lead:phone")
    m = send(u, text="/start")                         # /start сбрасывает заявку
    assert "Здравствуйте" in to_user(m, 8)[0]
    send(u, text="сколько стоит?")
    assert _ai_calls == ["сколько стоит?"]


def test_normal_question_still_goes_to_ai():
    u = {"id": 9, "first": "Вера"}
    m = send(u, text="Сколько стоит маникюр?")
    assert _ai_calls == ["Сколько стоит маникюр?"] and to_user(m, 9) == ["ответ модели"]


def test_admin_unreachable():
    u = {"id": 10, "first": "Даша", "username": "d"}
    send(u, text="Связаться с мастером")
    _bot.fail_admin = True
    try:
        m = send(u, data="lead:telegram")
    finally:
        _bot.fail_admin = False
    assert "не удалось передать заявку" in to_user(m, 10)[0]
    assert not any("заявка принята" in t for t in to_user(m, 10))


def test_lead_spam_limit():
    u = {"id": 11, "first": "Спам", "username": "s"}
    results = []
    for _ in range(6):
        send(u, text="Связаться с мастером")
        results.append(send(u, data="lead:telegram"))
    assert all(to_admin(r) for r in results[:5])
    assert not to_admin(results[5]) and "уже приняты" in to_user(results[5], 11)[0]


def test_non_text_in_flow():
    u = {"id": 12, "first": "Нина"}
    send(u, text="Связаться с мастером"); send(u, data="lead:email")
    sent.clear()
    upd = Update.model_validate({"update_id": 999, "message": {"message_id": 99, "date": 0,
        "chat": {"id": 12, "type": "private"}, "from": {"id": 12, "is_bot": False, "first_name": "Нина"},
        "sticker": {"file_id": "x", "file_unique_id": "y", "type": "regular", "width": 1, "height": 1,
                    "is_animated": False, "is_video": False}}})
    asyncio.run(_dp.feed_update(_bot, upd))
    assert "текстом" in to_user(sent, 12)[0]
