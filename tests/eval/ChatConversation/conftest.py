"""Fixtures of the ChatConversation eval (FULL production graph, ALL models real).

ChatConversation replays scripted multi-turn conversations through the production ChatGraph —
real analyze LLM, real generate LLM, real embeddings + Qdrant over the frozen 50-game corpus,
real checkpointer-backed memory. It is the only suite where the whole turn lifecycle
(analyze → route → retrieve → generate, with state accumulating across turns) runs end-to-end:
TurnAnalyzer/ChatRetrieve/ChatPitch each measure one node in isolation; this one measures
whether the conversation HOLDS UP.

Scoring and run persistence live in `report.ConversationReport` (shared mechanics in
`tests/eval/report/eval_report.py`); this conftest only wires fixtures and delegates the
session hooks. The checks and the case taxonomy are documented in `test_conversation.py`.

Both LLMs are built EXACTLY like production's defaults (same models, same temperatures, same
structured-output schemas — see ChatGraph.__init__ / ChatAdvisor.__init__) minus the trace
callbacks, so eval runs don't pollute the production `traces` table. The corpus collection is
built once per session from the FROZEN post-pipeline corpus (the same one ChatRetrieve
searches), on a DEDICATED throwaway collection deleted at teardown; the in-memory checkpointer
replaces the sqlite file so sessions never leak across runs.

    docker exec seller-api python -m pytest tests/eval/ChatConversation -q
"""

import json
from pathlib import Path

import pytest

from tests.eval.ChatConversation.report import ConversationReport

FROZEN = Path(__file__).resolve().parents[2] / "fixtures" / "suites" / "core" / "games_enriched.json"
COLLECTION = "games_eval_chat_conversation"


def pytest_sessionstart(session):
    # One report per suite, suite-namespaced: every eval conftest's hooks fire in a combined
    # `pytest tests/eval` session, so a shared attribute would mix the suites' records.
    session._chat_conversation_report = ConversationReport(Path(__file__).parent / "runs")


def pytest_sessionfinish(session, exitstatus):
    report = getattr(session, "_chat_conversation_report", None)
    if report is not None:
        report.finish(int(exitstatus))


@pytest.fixture
def record_conversation(request):
    """Tests record one entry per conversation:
    {case, n_turns, n_turn_checks, turn_failures, converged, turns_to_converge, by_turn,
     filters_ok, proposal_ok, fallback_turns, trajectory, final_filters, expected, note}.
    The oracle booleans are None when the case declares no such oracle."""
    return request.session._chat_conversation_report.record


@pytest.fixture(scope="session")
def graph():
    """The production ChatGraph with every collaborator real (except trace callbacks).

    Real pieces: analyze LLM (temperature 0.0, TurnAnalysis schema), generate LLM (temperature
    0.4, ChatReply schema), strong LLM (the model-tiering target — settings.llm_model_strong or
    the default, a production no-op until a stronger model is configured), GameVectorStore
    (Ollama embeddings + Qdrant) on the dedicated collection, GameRetriever on top. The only
    substitution is the in-memory checkpointer instead of the sqlite file.
    """
    memory = pytest.importorskip("langgraph.checkpoint.memory")
    from langchain_ollama import ChatOllama

    from app.chat.advisor import ChatAdvisor
    from app.chat.graph import ChatGraph
    from app.chat.models.analysis import TurnAnalysis
    from app.chat.models.reply import ChatReply
    from app.config import settings
    from app.core.vector_store import GameVectorStore
    from app.ingestion.serializer import DocumentSerializer
    from app.models.game_doc import GameDoc
    from app.rag.retriever import GameRetriever

    # --- frozen post-pipeline corpus → throwaway collection (same recipe as ChatRetrieve) ----
    if not FROZEN.exists():
        pytest.skip("frozen corpus missing — run: docker compose exec seller-api "
                    "python -m tests.eval.GameRetriever.freeze_corpus")
    serializer = DocumentSerializer()
    composed = [GameDoc(**d) for d in json.loads(FROZEN.read_text(encoding="utf-8"))]
    documents = [serializer.to_document(g) for g in composed]
    ids = [GameVectorStore.point_id(g.id_product) for g in composed]

    store = GameVectorStore(collection_name=COLLECTION)
    store.index(documents, ids=ids, recreate=True)

    analyze_llm = ChatOllama(
        model=settings.llm_model, base_url=settings.ollama_url, temperature=0.0,
    ).with_structured_output(TurnAnalysis)
    pitch_llm = ChatOllama(
        model=settings.llm_model, base_url=settings.ollama_url, temperature=0.4,
    ).with_structured_output(ChatReply)
    strong_llm = ChatOllama(
        model=settings.llm_model_strong or settings.llm_model,
        base_url=settings.ollama_url, temperature=0.4,
    ).with_structured_output(ChatReply)

    saver_cls = getattr(memory, "InMemorySaver", None) or memory.MemorySaver
    graph = ChatGraph(
        advisor=ChatAdvisor(retriever=GameRetriever(store=store), llm=pitch_llm),
        analyze_llm=analyze_llm,
        strong_llm=strong_llm,
        checkpointer=saver_cls(),
    )
    try:
        yield graph
    finally:
        store.client.delete_collection(COLLECTION)
