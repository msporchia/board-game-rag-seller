"""Retrieve games from the vector store (hybrid search).

Phase 2 was purely semantic. Phase 3 adds structured constraints (`SearchFilters`):
- HARD constraints become a Qdrant `query_filter` (pre-filter → excludes non-matches before the
  semantic ranking);
- SOFT constraints (`strict=False`) do not exclude: we over-fetch and re-rank, boosting the games
  that satisfy them (see `app/rag/filters.py`).
"""

from app.core.vector_store import GameVectorStore
from app.models import GameHit
from app.rag.filters import SearchFilters, rerank_soft

# When soft constraints are present we fetch more candidates than k, so the boost can reorder a
# wider pool before we cut to k.
SOFT_OVERSAMPLE = 4


class GameRetriever:
    def __init__(self, store: GameVectorStore | None = None):
        self.store = store or GameVectorStore()

    def search(self, query: str, k: int = 5, filters: SearchFilters | None = None) -> list[GameHit]:
        query_filter = filters.hard_filter() if filters else None
        soft = filters.soft_predicates() if filters else []

        fetch_k = k * SOFT_OVERSAMPLE if soft else k
        results = self.store.search(query, k=fetch_k, query_filter=query_filter)
        if soft:
            results = rerank_soft(results, soft)[:k]

        return [GameHit(score=float(score), **doc.metadata) for doc, score in results]
