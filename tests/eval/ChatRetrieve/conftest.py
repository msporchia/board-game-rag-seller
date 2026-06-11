"""Fixtures of the ChatRetrieve eval (embeddings + Qdrant, NO generation LLM).

The retrieve node of the stateful chat is the step that decides WHICH games even get a chance
to be pitched: it assembles the query from the conversation (previous user turns + current
message + unparsed click leftovers), merges quick-reply clicks into structured filters, and
runs the hybrid search. This suite measures that step in isolation, against a real ~50-game
corpus indexed with real embeddings — no analyze/generate LLM in the loop, so a run is fast
and near-deterministic.

Scoring and run persistence live in `report.RetrieveReport` (shared mechanics in
`tests/eval/report/eval_report.py`); this conftest only wires fixtures and delegates the
session hooks.

The corpus collection is built ONCE per session from the FROZEN post-pipeline corpus
(tests/fixtures/suites/core/games_enriched.json — the shared 50 games after the offline
production chain, see tests/eval/GameRetriever/freeze_corpus.py): the retrieve node must be
measured over the text it searches in PRODUCTION, not over raw catalog marketing run through
the rule-only e2e distractor recipe (which this suite used before — that baseline is not
comparable). Indexing happens on a DEDICATED throwaway collection
(`games_eval_chat_retrieve`), deleted at teardown. The production `games` collection is never
touched.

    docker exec seller-api python -m pytest tests/eval/ChatRetrieve -q
"""

import json
from pathlib import Path

import pytest

from tests.eval.ChatRetrieve.report import RetrieveReport

FROZEN = Path(__file__).resolve().parents[2] / "fixtures" / "suites" / "core" / "games_enriched.json"
COLLECTION = "games_eval_chat_retrieve"


def pytest_sessionstart(session):
    # One report per suite, suite-namespaced: every eval conftest's hooks fire in a combined
    # `pytest tests/eval` session, so a shared attribute would mix the suites' records.
    session._chat_retrieve_report = RetrieveReport(Path(__file__).parent / "runs")


def pytest_sessionfinish(session, exitstatus):
    report = getattr(session, "_chat_retrieve_report", None)
    if report is not None:
        report.finish(int(exitstatus))


@pytest.fixture
def record_retrieval(request):
    """Tests record one entry per case:
    {case, expected_id, k_used, rank (1-based or null), hit, note}."""
    return request.session._chat_retrieve_report.record


@pytest.fixture(scope="session")
def graph():
    """The production ChatGraph, wired to a throwaway corpus collection.

    Real pieces: GameVectorStore (Ollama embeddings + Qdrant) on the dedicated collection,
    GameRetriever on top of it, and the graph's own `_retrieve` logic. Faked pieces: the
    analyze and generate LLMs (reused from the ChatGraph unit fakes — they are never invoked
    by `_retrieve`, but injecting them keeps the constructor offline) and an in-memory
    checkpointer instead of the sqlite file.
    """
    memory = pytest.importorskip("langgraph.checkpoint.memory")
    from app.chat.advisor import ChatAdvisor
    from app.chat.graph import ChatGraph
    from app.chat.models.reply import ChatReply
    from app.core.vector_store import GameVectorStore
    from app.ingestion.serializer import DocumentSerializer
    from app.models.game_doc import GameDoc
    from app.rag.retriever import GameRetriever
    from tests.unit.ChatGraph.fakes import FakeAnalyzeLLM, FakeGenLLM

    # --- frozen post-pipeline corpus → throwaway collection (embeddings only, no LLM) -------
    if not FROZEN.exists():
        pytest.skip("frozen corpus missing — run: docker compose exec seller-api "
                    "python -m tests.eval.GameRetriever.freeze_corpus")
    serializer = DocumentSerializer()
    composed = [GameDoc(**d) for d in json.loads(FROZEN.read_text(encoding="utf-8"))]
    documents = [serializer.to_document(g) for g in composed]
    ids = [GameVectorStore.point_id(g.id_product) for g in composed]

    store = GameVectorStore(collection_name=COLLECTION)
    store.index(documents, ids=ids, recreate=True)

    saver_cls = getattr(memory, "InMemorySaver", None) or memory.MemorySaver
    graph = ChatGraph(
        advisor=ChatAdvisor(retriever=GameRetriever(store=store), llm=FakeGenLLM(ChatReply())),
        analyze_llm=FakeAnalyzeLLM(),
        strong_llm=FakeGenLLM(ChatReply()),
        checkpointer=saver_cls(),
    )
    try:
        yield graph
    finally:
        store.client.delete_collection(COLLECTION)
