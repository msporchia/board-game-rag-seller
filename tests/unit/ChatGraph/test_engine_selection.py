"""`POST /chat` engine selection (docs/idee.md §Q) — CHAT_ENGINE default + per-request override.

Purpose: lock the selection ladder on the stateful path: `ChatRequest.engine` wins when
present, otherwise `settings.chat_engine` decides; the selected NAME is what reaches
`_get_engine` (whose lazy engine construction is not under test here — the handler is called
directly with a capturing fake, no langgraph, no Ollama).
"""

import pytest

from app.chat.models.request import ChatRequest
from app.chat.models.response import ChatResponse


@pytest.fixture
def capture_engine(monkeypatch):
    """Patch `_get_engine` to record the resolved name and serve a canned engine."""
    import app.api.chat as chat_api

    selected: list[str] = []

    class FakeEngine:
        def reply(self, message, choices=None, k=5, session_id=None):
            return ChatResponse(message="ok")

    def _get_engine(name):
        selected.append(name)
        return FakeEngine()

    monkeypatch.setattr(chat_api, "_get_engine", _get_engine)
    return selected


class TestEngineSelection:
    def test_default_is_the_settings_engine(self, capture_engine):
        import app.api.chat as chat_api

        chat_api.chat(ChatRequest(message="ciao", session_id="s1"))

        assert capture_engine == ["pipeline"]  # settings.chat_engine default

    def test_settings_engine_decides_without_an_override(self, capture_engine, monkeypatch):
        import app.api.chat as chat_api

        monkeypatch.setattr(chat_api.settings, "chat_engine", "piloted")
        chat_api.chat(ChatRequest(message="ciao", session_id="s1"))

        assert capture_engine == ["piloted"]

    def test_request_override_wins_over_settings(self, capture_engine, monkeypatch):
        import app.api.chat as chat_api

        monkeypatch.setattr(chat_api.settings, "chat_engine", "piloted")
        chat_api.chat(ChatRequest(message="ciao", session_id="s1", engine="pipeline"))

        assert capture_engine == ["pipeline"]

    def test_request_can_opt_into_piloted(self, capture_engine):
        import app.api.chat as chat_api

        chat_api.chat(ChatRequest(message="ciao", session_id="s1", engine="piloted"))

        assert capture_engine == ["piloted"]

    def test_stateless_path_ignores_the_engine_field(self, capture_engine, monkeypatch):
        import app.api.chat as chat_api

        calls = []

        class FakeAdvisor:
            def reply(self, message, choices=None, k=5):
                calls.append(message)
                return ChatResponse(message="stateless")

        monkeypatch.setattr(chat_api, "_advisor", FakeAdvisor())
        res = chat_api.chat(ChatRequest(message="ciao", engine="piloted"))

        assert res.message == "stateless"
        assert calls == ["ciao"] and capture_engine == []
