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
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": n} for n in (models or [])]})

    return httpx.MockTransport(handler)


def test_check_server_ok(monkeypatch):
    monkeypatch.setattr(ai, "OLLAMA_MODEL", "qwen2.5:7b")
    assert _run(ai.check_server(_transport(["qwen2.5:7b"]))) is None


def test_check_server_latest_tag(monkeypatch):
    monkeypatch.setattr(ai, "OLLAMA_MODEL", "llama3.2")
    assert _run(ai.check_server(_transport(["llama3.2:latest"]))) is None


def test_check_server_model_missing(monkeypatch):
    monkeypatch.setattr(ai, "OLLAMA_MODEL", "qwen2.5:7b")
    msg = _run(ai.check_server(_transport(["llama3.2:latest"])))
    assert "ollama pull qwen2.5:7b" in msg


def test_check_server_down():
    msg = _run(ai.check_server(_transport(fail=True)))
    assert "Ollama" in msg and "ollama serve" in msg


def test_ask_sends_system_and_user_and_strips_think(monkeypatch):
    captured = {}

    async def fake_create(**kw):
        captured.update(kw)
        content = "<think>долго думаю</think>\nМаникюр стоит 1 800 ₽."
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    monkeypatch.setattr(ai._client.chat.completions, "create", fake_create)
    answer = _run(ai.ask("Сколько стоит маникюр?"))
    assert answer == "Маникюр стоит 1 800 ₽."
    assert [m["role"] for m in captured["messages"]] == ["system", "user"]
    assert captured["model"] == ai.OLLAMA_MODEL
