"""Fixtures LOCAL to the ChatGraph unit — fully offline, no Ollama, no Qdrant, no files.

The graph talks to three LLM-shaped collaborators (the analyzer, the default pitch model, the
strong escalation model) and one retriever; we fake all four so the tests assert the GRAPH's own
logic — routing, clicks→filters, memory, tiering — not the models. Persistence uses LangGraph's
in-memory checkpointer (the sqlite one is a deployment detail, same interface).

`FakeAnalyzeLLM` takes a QUEUE of TurnAnalysis: one entry per turn, the last one repeating —
so a test can script how the "user" comes across turn by turn.

Note: tests that build the graph require `langgraph` (skipped cleanly when not installed);
the choices-parser and API-bypass tests in this package do not.
"""

import pytest

from app.chat.advisor import ChatAdvisor
from app.chat.models.analysis import TurnAnalysis
from app.chat.models.recommendation import ChatRecommendation
from app.chat.models.reply import ChatReply
from app.models.game_hit import GameHit


def make_hit(id_product: int, name: str, **overrides) -> GameHit:
    data = {"score": 0.9, "id_product": id_product, "name": name}
    data.update(overrides)
    return GameHit(**data)


class FakeRetriever:
    """Returns a preset list of hits (cut to k); records (query, k, filters) per call."""

    def __init__(self, hits: list[GameHit]):
        self.hits = hits
        self.calls: list[tuple] = []

    def search(self, query: str, k: int = 5, filters=None) -> list[GameHit]:
        self.calls.append((query, k, filters))
        return self.hits[:k]


class FakeAnalyzeLLM:
    """`.invoke()` returns the scripted TurnAnalysis queue, repeating the last entry."""

    def __init__(self, analyses: list[TurnAnalysis] | None = None, raises: bool = False):
        self.analyses = list(analyses or [])
        self.raises = raises
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> TurnAnalysis:
        self.calls.append(prompt)
        if self.raises:
            raise RuntimeError("analyzer transport failure")
        if not self.analyses:
            return TurnAnalysis()
        return self.analyses.pop(0) if len(self.analyses) > 1 else self.analyses[0]


class FakeGenLLM:
    """`.invoke()` returns a preset ChatReply; records prompts (to assert WHICH model ran)."""

    def __init__(self, reply: ChatReply):
        self.reply = reply
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> ChatReply:
        self.calls.append(prompt)
        return self.reply


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
