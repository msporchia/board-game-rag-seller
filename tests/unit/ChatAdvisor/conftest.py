"""Fixtures LOCAL to the ChatAdvisor unit — fully offline, no Ollama, no Qdrant.

The advisor talks to two collaborators: a retriever (`.search → list[GameHit]`) and a
structured LLM (`.invoke → ChatReply`, i.e. intro + per-game {id, pitch} recommendations). We
fake both so the tests are deterministic and assert the advisor's own logic —
grounding/validation, message assembly, fallback, contract shape — not the model.

`FakeStructuredLLM` returns a preset `ChatReply` (the advisor wires `with_structured_output`, so
the real transport hands back a parsed object, not raw text) — or raises, to drive the
fallback path.
"""

import pytest

from app.chat.advisor import ChatAdvisor
from app.chat.models.reply import ChatReply
from app.models.game_hit import GameHit


def make_hit(id_product: int, name: str, **overrides) -> GameHit:
    data = {"score": 0.9, "id_product": id_product, "name": name}
    data.update(overrides)
    return GameHit(**data)


class FakeRetriever:
    """Returns a preset list of hits; records the queries it received."""

    def __init__(self, hits: list[GameHit]):
        self.hits = hits
        self.calls: list[tuple] = []

    def search(self, query: str, k: int = 5, filters=None) -> list[GameHit]:
        self.calls.append((query, k, filters))
        return self.hits[:k]


class FakeStructuredLLM:
    """`.invoke()` ignores the prompt and returns a preset ChatReply (or raises)."""

    def __init__(self, reply: ChatReply | None = None, raises: bool = False):
        self.reply = reply
        self.raises = raises
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> ChatReply:
        self.calls.append(prompt)
        if self.raises:
            raise RuntimeError("LLM transport failure")
        return self.reply


@pytest.fixture
def make_advisor():
    def _make(hits: list[GameHit] | None = None, reply: ChatReply | None = None,
              raises: bool = False):
        retriever = FakeRetriever(hits or [])
        llm = FakeStructuredLLM(reply=reply, raises=raises)
        advisor = ChatAdvisor(retriever=retriever, llm=llm)
        return advisor, retriever, llm

    return _make
