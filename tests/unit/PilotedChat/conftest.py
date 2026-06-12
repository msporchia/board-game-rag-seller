"""Fixtures LOCAL to the PilotedChat unit — fully offline, no Ollama, no Qdrant, no files.

The fakes live in `fakes.py`; here only the `make_piloted` factory fixture. Persistence uses
LangGraph's in-memory checkpointer (the sqlite one is a deployment detail, same interface).
The default pitch reply recommends the first two default hits, so grounding keeps it intact
unless a test scripts otherwise.
"""

import pytest

from app.chat.advisor import ChatAdvisor
from app.chat.models.intent import SearchIntent
from app.chat.models.recommendation import ChatRecommendation
from app.chat.models.reply import ChatReply
from app.chat.models.retry import RetryDecision
from app.models.game_hit import GameHit
from tests.unit.PilotedChat.fakes import (FakeIntentLLM, FakePitchLLM, FakeRetryLLM,
                                          FakeSearchRetriever, make_hit)


@pytest.fixture
def make_piloted():
    memory = pytest.importorskip("langgraph.checkpoint.memory")
    from app.chat.piloted import PilotedChat

    saver_cls = getattr(memory, "InMemorySaver", None) or memory.MemorySaver

    def _make(results: list[list[GameHit]] | None = None,
              intents: list[SearchIntent] | None = None,
              decisions: list[RetryDecision] | None = None,
              reply: ChatReply | None = None,
              intent_raises: bool = False, retry_raises: bool = False):
        hits = [make_hit(i, f"G{i}") for i in (1, 2, 3, 4, 5)]
        retriever = FakeSearchRetriever(results if results is not None else [hits])
        pitch = FakePitchLLM(reply or ChatReply(
            intro="Ti propongo questi!",
            recommendations=[ChatRecommendation(id=h.id_product, pitch=f"{h.name} fa per voi.")
                             for h in hits[:2]],
            quick_replies=["per 2 giocatori", "max 60 minuti"],
        ))
        intent = FakeIntentLLM(intents, raises=intent_raises)
        retry = FakeRetryLLM(decisions, raises=retry_raises)
        engine = PilotedChat(
            advisor=ChatAdvisor(retriever=retriever, llm=pitch),
            intent_llm=intent,
            retry_llm=retry,
            checkpointer=saver_cls(),
        )
        return engine, retriever, intent, retry, pitch

    return _make
