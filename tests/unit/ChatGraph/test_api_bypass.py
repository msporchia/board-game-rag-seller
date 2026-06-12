"""`POST /chat` routing — Phase 4/Phase 5 split on `session_id` (backward compatibility).

Purpose: lock that a request WITHOUT `session_id` takes the original stateless advisor path and
never touches the engine (no checkpointer, no langgraph import), while a request WITH it goes to
the tiered engine (TieredChat over the graph) keyed by that id. The handler is called directly
with fakes monkeypatched in — no HTTP, no Ollama, no Qdrant.
"""

import pytest

from app.chat.models.request import ChatRequest
from app.chat.models.response import ChatResponse


class TestSessionRouting:
    def test_no_session_id_bypasses_the_graph(self, monkeypatch):
        import app.api.chat as chat_api

        calls = []

        class FakeAdvisor:
            def reply(self, message, choices=None, k=5):
                calls.append((message, choices, k))
                return ChatResponse(message="stateless")

        monkeypatch.setattr(chat_api, "_advisor", FakeAdvisor())
        monkeypatch.setattr(chat_api, "_get_engine",
                            lambda name: pytest.fail("a stateless request must not build the engine"))

        res = chat_api.chat(ChatRequest(message="ciao"))

        assert res.message == "stateless"
        assert calls == [("ciao", [], 5)]

    def test_session_id_routes_to_the_engine(self, monkeypatch):
        import app.api.chat as chat_api

        class FakeEngine:
            def __init__(self):
                self.calls = []

            def reply(self, message, choices=None, k=5, session_id=None):
                self.calls.append((message, session_id))
                return ChatResponse(message="stateful")

        fake = FakeEngine()
        monkeypatch.setattr(chat_api, "_get_engine", lambda name: fake)
        monkeypatch.setattr(
            chat_api, "_advisor",
            type("Boom", (), {"reply": lambda *a, **kw: pytest.fail("graph path expected")})())

        res = chat_api.chat(ChatRequest(message="ciao", session_id="s1"))

        assert res.message == "stateful"
        assert fake.calls == [("ciao", "s1")]
