"""Retrieve games from the vector store (semantic search).

Phase 2: purely semantic search. In Phase 3 the structured filters (hybrid search) are added
by passing a `query_filter` to GameVectorStore.search.
"""

from app.core.vector_store import GameVectorStore
from app.models import GameHit


class GameRetriever:
    def __init__(self, store: GameVectorStore | None = None):
        self.store = store or GameVectorStore()

    def search(self, query: str, k: int = 5) -> list[GameHit]:
        results = self.store.search(query, k=k)
        return [GameHit(score=float(score), **doc.metadata) for doc, score in results]
