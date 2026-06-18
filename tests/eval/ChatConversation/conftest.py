"""Fixtures of the ChatConversation eval (FULL production engine, ALL models real).

ChatConversation replays scripted multi-turn conversations through the production engine of
the arm under eval (docs/idee.md §Q) — real LLM steps, real embeddings + Qdrant over the
frozen 50-game corpus, real checkpointer-backed memory. It is the only suite where the whole
turn lifecycle runs end-to-end with state accumulating across turns: the per-node suites
measure one step in isolation; this one measures whether the conversation HOLDS UP.

THE ARM IS SWITCHED BY ENV, same knob as production (`CHAT_ENGINE`, read through settings):
- pipeline (default): the decomposed graph — analyze → route → retrieve → generate.
- piloted: arm B — intent → search → explicit zero-result retry → generate.
- agent: the tool-calling engine — the model drives `search_catalog` itself, in-process session
  memory; black-box, so it is measured end-to-end (no per-turn state spying). Point it at a
  tool-capable model via `LLM_MODEL_STRONG` (e.g. qwen2.5:7b — fits the 8GB-VRAM dev box).
Same fixtures, same corpus, same oracles: the RESULTS delta between two consecutive runs IS
the arm comparison. Every real model carries the LLMUsageTracker callback, so each
conversation records its LLM calls and Ollama token counts — the cost denominator next to the
quality numbers.

    docker compose exec seller-api python -m pytest tests/eval/ChatConversation -q
    docker compose exec -e CHAT_ENGINE=piloted seller-api python -m pytest tests/eval/ChatConversation -q
    docker compose exec -e CHAT_ENGINE=agent -e LLM_MODEL_STRONG=qwen2.5:7b seller-api python -m pytest tests/eval/ChatConversation -q

Both arms' LLMs are built EXACTLY like production's defaults (same models, same temperatures,
same structured-output schemas) minus the trace callbacks, so eval runs don't pollute the
production `traces` table. The corpus collection is built once per session from the FROZEN
post-pipeline corpus, on a DEDICATED throwaway collection deleted at teardown; the in-memory
checkpointer replaces the sqlite file so sessions never leak across runs.
"""

import json
from pathlib import Path

import pytest

from tests.eval.ChatConversation.report import ConversationReport
from tests.eval.ChatConversation.usage import LLMUsageTracker

FROZEN = Path(__file__).resolve().parents[2] / "fixtures" / "suites" / "core" / "games_enriched.json"
COLLECTION = "games_eval_chat_conversation"


def _engine_name() -> str:
    from app.config import settings
    return settings.chat_engine if settings.chat_engine in ("piloted", "agent") else "pipeline"


def pytest_sessionstart(session):
    # One report per suite, suite-namespaced: every eval conftest's hooks fire in a combined
    # `pytest tests/eval` session, so a shared attribute would mix the suites' records.
    session._chat_conversation_report = ConversationReport(Path(__file__).parent / "runs",
                                                           engine=_engine_name())


def pytest_sessionfinish(session, exitstatus):
    report = getattr(session, "_chat_conversation_report", None)
    if report is not None:
        report.finish(int(exitstatus))


@pytest.fixture
def record_conversation(request):
    """Tests record one entry per conversation:
    {case, n_turns, n_turn_checks, turn_failures, converged, turns_to_converge, by_turn,
     filters_ok, proposal_ok, fallback_turns, llm_calls, tokens_in, tokens_out, trajectory,
     final_filters, expected, note}.
    The oracle booleans are None when the case declares no such oracle."""
    return request.session._chat_conversation_report.record


@pytest.fixture(scope="session")
def llm_usage():
    """One tracker for the whole session, attached to every real model the engine uses;
    tests snapshot it around each conversation to get per-conversation deltas."""
    return LLMUsageTracker()


@pytest.fixture(scope="session")
def graph(llm_usage):
    """The production engine of the arm under eval, every collaborator real.

    Real pieces per arm — pipeline: analyze LLM (temperature 0.0, TurnAnalysis schema),
    generate LLM (temperature 0.4, ChatReply schema), strong LLM (the model-tiering target);
    piloted: intent LLM (temperature 0.0, SearchIntent schema), retry LLM (temperature 0.0,
    RetryDecision schema), the same generate LLM. Shared by both: GameVectorStore (Ollama
    embeddings + Qdrant) on the dedicated collection, GameRetriever on top. The only
    substitution is the in-memory checkpointer instead of the sqlite file.
    """
    memory = pytest.importorskip("langgraph.checkpoint.memory")
    from langchain_ollama import ChatOllama

    from app.chat.advisor import ChatAdvisor
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

    pitch_llm = ChatOllama(
        model=settings.llm_model, base_url=settings.ollama_url, temperature=0.4,
        callbacks=[llm_usage],
    ).with_structured_output(ChatReply)
    advisor = ChatAdvisor(retriever=GameRetriever(store=store), llm=pitch_llm)
    saver_cls = getattr(memory, "InMemorySaver", None) or memory.MemorySaver

    if _engine_name() == "piloted":
        from app.chat.models.intent import SearchIntent
        from app.chat.models.retry import RetryDecision
        from app.chat.piloted import PilotedChat

        intent_llm = ChatOllama(
            model=settings.llm_model, base_url=settings.ollama_url, temperature=0.0,
            callbacks=[llm_usage],
        ).with_structured_output(SearchIntent)
        retry_llm = ChatOllama(
            model=settings.llm_model, base_url=settings.ollama_url, temperature=0.0,
            callbacks=[llm_usage],
        ).with_structured_output(RetryDecision)
        engine = PilotedChat(advisor=advisor, intent_llm=intent_llm, retry_llm=retry_llm,
                             checkpointer=saver_cls())
    elif _engine_name() == "agent":
        from app.chat.agentic import AgenticChat

        # The agent uses ONE model for the tool loop AND the pitch (set it via LLM_MODEL_STRONG):
        # on the 8GB-VRAM dev box a single resident model + the tiny embedder avoids the model-swap
        # thrashing a 14B+separate-pitch turn hit (the 2026-06-18 finding). qwen2.5:7b is
        # non-reasoning, so the structured-output pitch is fine without a /no_think dance.
        agent_model = settings.llm_model_strong or settings.llm_model
        agent_pitch = ChatOllama(
            model=agent_model, base_url=settings.ollama_url, temperature=0.4,
            callbacks=[llm_usage],
        ).with_structured_output(ChatReply)
        agent_advisor = ChatAdvisor(retriever=GameRetriever(store=store), llm=agent_pitch)
        agent_llm = ChatOllama(
            model=agent_model, base_url=settings.ollama_url, temperature=0.2,
            callbacks=[llm_usage],
        )
        engine = AgenticChat(advisor=agent_advisor, llm=agent_llm)
    else:
        from app.chat.graph import ChatGraph
        from app.chat.models.analysis import TurnAnalysis

        analyze_llm = ChatOllama(
            model=settings.llm_model, base_url=settings.ollama_url, temperature=0.0,
            callbacks=[llm_usage],
        ).with_structured_output(TurnAnalysis)
        strong_llm = ChatOllama(
            model=settings.llm_model_strong or settings.llm_model,
            base_url=settings.ollama_url, temperature=0.4,
            callbacks=[llm_usage],
        ).with_structured_output(ChatReply)
        engine = ChatGraph(advisor=advisor, analyze_llm=analyze_llm, strong_llm=strong_llm,
                           checkpointer=saver_cls())
    try:
        yield engine
    finally:
        store.client.delete_collection(COLLECTION)
