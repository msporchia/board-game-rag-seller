"""Fixtures LOCAL to the ChatGraph unit — fully offline, no Ollama, no Qdrant, no files.

The fakes live in `fakes.py`; here only the `make_graph` factory fixture. Persistence uses
LangGraph's in-memory checkpointer (the sqlite one is a deployment detail, same interface).

Note: tests that build the graph require `langgraph` (skipped cleanly when not installed);
the choices-parser and API-bypass tests in this package do not.
"""

import pytest

from app.chat.advisor import ChatAdvisor
from app.chat.models.analysis import TurnAnalysis
from app.chat.models.recommendation import ChatRecommendation
from app.chat.models.reply import ChatReply
from app.models.game_hit import GameHit
from tests.unit.ChatGraph.fakes import FakeAnalyzeLLM, FakeGenLLM, FakeRetriever, make_hit


@pytest.fixture
def make_graph():
    memory = pytest.importorskip("langgraph.checkpoint.memory")
    from app.chat.graph import ChatGraph

    saver_cls = getattr(memory, "InMemorySaver", None) or memory.MemorySaver

    def _make(hits: list[GameHit] | None = None, analyses: list[TurnAnalysis] | None = None,
              reply: ChatReply | None = None, strong_reply: ChatReply | None = None):
        hits = hits if hits is not None else [make_hit(i, f"G{i}") for i in (1, 2, 3, 4, 5)]
        retriever = FakeRetriever(hits)
        gen = FakeGenLLM(reply or ChatReply(
            intro="Ti propongo questi!",
            recommendations=[ChatRecommendation(id=h.id_product, pitch=f"{h.name} fa per voi.")
                             for h in hits[:2]],
            quick_replies=["per 2 giocatori", "max 60 minuti"],
        ))
        strong = FakeGenLLM(strong_reply or ChatReply(
            intro="Risposta dal modello forte.",
            recommendations=([ChatRecommendation(id=hits[0].id_product,
                                                 pitch=f"{hits[0].name} è la scelta giusta.")]
                             if hits else []),
        ))
        graph = ChatGraph(
            advisor=ChatAdvisor(retriever=retriever, llm=gen),
            analyze_llm=FakeAnalyzeLLM(analyses),
            strong_llm=strong,
            checkpointer=saver_cls(),
        )
        return graph, retriever, gen, strong

    return _make
