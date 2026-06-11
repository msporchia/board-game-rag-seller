"""Fixtures of the GameRetriever ranking eval (embeddings + Qdrant, NO LLM in the loop).

The suite measures the RANKING the retriever produces over the data it sees in PRODUCTION:
the corpus is `games_enriched.json` — the shared 50-game corpus frozen AFTER the offline
production chain (Curator → Synth → Compose, see `freeze_corpus.py`) — not the raw catalog
marketing. The enrichment LLM already ran at freeze time, so a run is fast and
near-deterministic: only the embedder and Qdrant are live.

The corpus is indexed ONCE per session on a DEDICATED throwaway collection
(`games_eval_ranking`), deleted at teardown. The production `games` collection is never
touched. Scoring and run persistence live in `report.RankingReport`.

    docker compose exec seller-api python -m pytest tests/eval/GameRetriever -q
"""

import json
from pathlib import Path

import pytest

from tests.eval.GameRetriever.report import RankingReport

FROZEN = Path(__file__).resolve().parents[2] / "fixtures" / "suites" / "core" / "games_enriched.json"
COLLECTION = "games_eval_ranking"


def pytest_sessionstart(session):
    # Suite-namespaced report: every eval conftest's hooks fire in a combined
    # `pytest tests/eval` session, so a shared attribute would mix the suites' records.
    session._game_ranking_report = RankingReport(Path(__file__).parent / "runs")


def pytest_sessionfinish(session, exitstatus):
    report = getattr(session, "_game_ranking_report", None)
    if report is not None:
        report.finish(int(exitstatus))


@pytest.fixture
def record_ranking(request):
    """Tests record one entry per case:
    {case, query, oracle: [{id, name, expected_pos, rank}], window, note}."""
    return request.session._game_ranking_report.record


@pytest.fixture(scope="session")
def corpus() -> list:
    """The frozen post-pipeline GameDocs. Skips with instructions if not frozen yet."""
    from app.models.game_doc import GameDoc
    if not FROZEN.exists():
        pytest.skip("frozen corpus missing — run: docker compose exec seller-api "
                    "python -m tests.eval.GameRetriever.freeze_corpus")
    return [GameDoc(**d) for d in json.loads(FROZEN.read_text(encoding="utf-8"))]


@pytest.fixture(scope="session")
def retriever(corpus):
    """The production GameRetriever over the enriched corpus, on a throwaway collection."""
    from app.core.vector_store import GameVectorStore
    from app.ingestion.serializer import DocumentSerializer
    from app.rag.retriever import GameRetriever

    serializer = DocumentSerializer()
    documents = [serializer.to_document(g) for g in corpus]
    ids = [GameVectorStore.point_id(g.id_product) for g in corpus]

    store = GameVectorStore(collection_name=COLLECTION)
    store.index(documents, ids=ids, recreate=True)
    try:
        yield GameRetriever(store=store)
    finally:
        store.client.delete_collection(COLLECTION)
