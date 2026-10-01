import asyncio
from types import SimpleNamespace

import httpx

from bot.services import ai


def _run(coro):
    return asyncio.run(coro)


def _transport(models=None, fail=False):
    def handler(request: httpx.Request) -> httpx.Response:
        if fail:
            raise httpx.ConnectError("refused")
        assert request.url.path in {"/models", "/v1/models"}
        return httpx.Response(200, json={"data": [{"id": n} for n in (models or [])]})

    return httpx.MockTransport(handler)


def test_check_server_ok(monkeypatch):
    monkeypatch.setattr(ai, "DEEPSEEK_API_KEY", "test-key")
    assert _run(ai.check_server(_transport(["deepseek-chat"]))) is None


def test_check_server_down(monkeypatch):
    monkeypatch.setattr(ai, "DEEPSEEK_API_KEY", "test-key")
    msg = _run(ai.check_server(_transport(fail=True)))
    assert "DeepSeek" in msg and "DEEPSEEK_API_KEY" in msg


def test_ask_sends_system_and_user_and_strips_think(monkeypatch):
    captured = {}

    async def fake_create(**kw):
        captured.update(kw)
        content = "<think>долго думаю</think>\nМаникюр стоит 1 800 ₽."
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    monkeypatch.setattr(ai, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(ai._client.chat.completions, "create", fake_create)
    answer = _run(ai.ask("Сколько стоит маникюр?"))
    assert answer == "Маникюр стоит 1 800 ₽."
    assert [m["role"] for m in captured["messages"]] == ["system", "user"]
    assert captured["model"] == ai.DEEPSEEK_MODEL
