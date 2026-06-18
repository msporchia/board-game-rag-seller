"""RetrievalContext — the live, mutable state of one turn's retrieval stage.

Policies wrapping `around_retrieve` read and mutate this freely: change the `query`, merge into
`filters_spec`, bump `k`, or even swap `retriever` for a decorated one (e.g. a fetcher that only
returns games on promotion). `execute()` is the stage's real work — the innermost `call_next`
the policy chain wraps — so the SearchFilters assembly lives in ONE place shared by every engine.
"""

from dataclasses import dataclass, field

from app.models.game_hit import GameHit
from app.rag.filters.search_filters import SearchFilters
from app.rag.retriever import GameRetriever


@dataclass
class RetrievalContext:
    query: str
    k: int
    retriever: GameRetriever  # duck-typed: anything with .search(query, k, filters)
    # The session's accumulated filter spec (graph/piloted path); policies merge into it.
    filters_spec: dict = field(default_factory=dict)
    # A pre-built SearchFilters (the stateless reply escape hatch); wins over filters_spec.
    filters: SearchFilters | None = None
    # Games to hard-exclude from the result set (Phase 6: the customer's owned games) — applied
    # as a Qdrant `must_not` at search time, not as a post-match filter.
    exclude_ids: list[int] | None = None

    def execute(self) -> list[GameHit]:
        """Run the actual hybrid search from the current context state."""
        filters = self.filters if self.filters is not None else (
            SearchFilters.from_dict(self.filters_spec) if self.filters_spec else None)
        return self.retriever.search(self.query, k=self.k, filters=filters,
                                     exclude_ids=self.exclude_ids)
