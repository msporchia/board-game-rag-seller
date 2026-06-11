"""Persistence + scoring of the ChatRetrieve eval (embeddings + Qdrant, NO generation LLM).

The retrieve node of the stateful chat is the step that decides WHICH games even get a chance
to be pitched: it assembles the query from the conversation (previous user turns + current
message + unparsed click leftovers), merges quick-reply clicks into structured filters, and
runs the hybrid search. This suite measures that step in isolation, against a real ~50-game
corpus indexed with real embeddings — no analyze/generate LLM in the loop, so a run is fast
and near-deterministic (embeddings are the only model involved, at temperature-free inference).

The corpus collection is built ONCE per session from the shared fixture corpus
(tests/fixtures/suites/core/games.json) through the exact deterministic recipe the e2e harness
uses for its distractors: `RuleComposeEnricher` (no LLM) → `DocumentSerializer` →
`GameVectorStore.index(recreate=True)` — on a DEDICATED throwaway collection
(`games_eval_chat_retrieve`), deleted at teardown. The production `games` collection is never
touched.

Scoring is recall@k (the headline: did the expected game make it onto the table at the k the
strategy dictates?) plus the mean rank of the targets that were found. Like the sibling evals,
there is no acceptance threshold yet: the first runs establish the baseline, the diff vs the
previous run flags regressions (`runs/retrieve_<timestamp>.json` + `runs/last.json`,
gitignored).

    docker exec seller-api python -m pytest tests/eval/ChatRetrieve -q
"""

import json
import time
from pathlib import Path

import pytest

RUNS = Path(__file__).parent / "runs"
CORPUS = Path(__file__).resolve().parents[2] / "fixtures" / "suites" / "core" / "games.json"
COLLECTION = "games_eval_chat_retrieve"


def pytest_sessionstart(session):
    RUNS.mkdir(exist_ok=True)
    # Suite-namespaced (not `_eval_records`): every eval conftest's hooks fire in a combined
    # `pytest tests/eval` session, so a shared attribute would mix the suites' records.
    session._chat_retrieve_records: list[dict] = []
    session._chat_retrieve_started = time.strftime("%Y%m%d-%H%M%S")


@pytest.fixture
def record_retrieval(request):
    """Tests record one entry per case:
    {case, expected_id, k_used, rank (1-based or null), hit, note}."""
    def _record(entry: dict) -> None:
        request.session._chat_retrieve_records.append(entry)
    return _record


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
    from app.ingestion.enricher.compose import RuleComposeEnricher
    from app.ingestion.serializer import DocumentSerializer
    from app.models.game_doc import GameDoc
    from app.rag.retriever import GameRetriever
    from tests.unit.ChatGraph.fakes import FakeAnalyzeLLM, FakeGenLLM

    # --- corpus → throwaway collection, the e2e distractor recipe (NO LLM, embeddings only) --
    compose = RuleComposeEnricher()
    serializer = DocumentSerializer()
    games = [GameDoc.from_dto(dto)
             for dto in json.loads(CORPUS.read_text(encoding="utf-8"))]
    composed = [compose.enrich(g) for g in games]
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


# ---- scoring ----------------------------------------------------------------

def _aggregate(records: list[dict]) -> dict:
    """recall@k (the headline) + mean rank of the found targets."""
    n = len(records)
    found = [r["rank"] for r in records if r["rank"] is not None]
    hits = sum(int(r["hit"]) for r in records)
    return {
        "n_cases": n,
        "recall_at_k": round(hits / n, 4) if n else 0.0,
        "found": len(found),
        "mean_rank": round(sum(found) / len(found), 2) if found else None,
    }


def _previous_metrics() -> dict | None:
    timestamped = sorted(p for p in RUNS.glob("retrieve_*.json"))
    if not timestamped:
        return None
    try:
        prev = json.loads(timestamped[-1].read_text(encoding="utf-8"))
    except Exception:                       # noqa: BLE001  corrupted file → ignore
        return None
    return prev.get("metrics")


def _format_delta(curr: float, prev: float | None) -> str:
    if prev is None:
        return f"{curr:.3f}"
    d = curr - prev
    arrow = "→" if abs(d) < 1e-4 else ("↑" if d > 0 else "↓")
    return f"{curr:.3f} {arrow} (Δ {d:+.3f}, was: {prev:.3f})"


def _print_summary(metrics: dict, prev: dict | None, records: list[dict], model: str) -> None:
    print("\n" + "=" * 70)
    print(f"  EVAL ChatRetrieve — _retrieve | embeddings: {model} | recall@k")
    print("=" * 70)
    print(f"  Cases: {metrics['n_cases']}   "
          f"recall@k: {_format_delta(metrics['recall_at_k'], (prev or {}).get('recall_at_k'))}")
    mean_rank = metrics["mean_rank"]
    prev_rank = (prev or {}).get("mean_rank")
    rank_note = f" (was: {prev_rank})" if prev_rank is not None else ""
    print(f"  Found: {metrics['found']}/{metrics['n_cases']}   "
          f"mean rank of found: {mean_rank}{rank_note}")
    print()
    for rec in records:
        mark = "✓" if rec["hit"] else "✗"
        rank = rec["rank"] if rec["rank"] is not None else "—"
        print(f"  {mark} {rec['case']:38s} rank {rank!s:>2s} / k={rec['k_used']}")
    print("=" * 70 + "\n")


def pytest_sessionfinish(session, exitstatus):
    records = getattr(session, "_chat_retrieve_records", None)
    if not records:
        return
    timestamp = session._chat_retrieve_started
    metrics = _aggregate(records)
    prev_metrics = _previous_metrics()

    payload = {
        "session": timestamp,
        "model": _peek_model(),
        "exit_status": int(exitstatus),
        "metrics": metrics,
        "records": records,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (RUNS / f"retrieve_{timestamp}.json").write_text(text, encoding="utf-8")
    (RUNS / "last.json").write_text(text, encoding="utf-8")

    _print_summary(metrics, prev_metrics, records, payload["model"])


def _peek_model() -> str:
    try:
        from app.config import settings
        return settings.embedding_model
    except Exception:                       # noqa: BLE001  settings unavailable → unknown
        return "unknown"
