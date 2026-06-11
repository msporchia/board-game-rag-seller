"""Fixtures LOCAL to the ChatAdvisor unit — fully offline, no Ollama, no Qdrant.
The fakes live in `fakes.py`; here only the `make_advisor` factory fixture."""

import pytest

from app.chat.advisor import ChatAdvisor
from app.chat.models.reply import ChatReply
from app.models.game_hit import GameHit
from tests.unit.ChatAdvisor.fakes import FakeRetriever, FakeStructuredLLM


@pytest.fixture
def make_advisor():
    def _make(hits: list[GameHit] | None = None, reply: ChatReply | None = None,
              raises: bool = False):
        retriever = FakeRetriever(hits or [])
        llm = FakeStructuredLLM(reply=reply, raises=raises)
        advisor = ChatAdvisor(retriever=retriever, llm=llm)
        return advisor, retriever, llm

    return _make
