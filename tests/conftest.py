import pytest

from bot import cart, config, guardrails
from bot.handlers import lead
from bot.services import ai
from tests import helpers


async def _fake_ask(question):
    helpers.ai_calls.append(question)
    return "ответ модели"


@pytest.fixture
def stand(monkeypatch):
    """Стенд для сквозных тестов: подмена модели, ADMIN_ID, лимита заявок; корзины очищаются.

    Подключается через pytestmark = pytest.mark.usefixtures("stand").
    """
    monkeypatch.setattr(ai, "ask", _fake_ask)
    monkeypatch.setattr(config, "ADMIN_ID", helpers.ADMIN)
    monkeypatch.setattr(lead, "_lead_limiter", guardrails.RateLimiter(limit=5, window=3600))
    cart.clear_all()
