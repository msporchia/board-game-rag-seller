"""Search endpoint.

Phase 2: semantic search (`GET /search?q=...&k=5`).
Phase 3: hybrid search — structured constraints over the indexed payload. The flat query params
are assembled into the per-field spec that `SearchFilters.from_dict` expects (the same shape an
LLM tool-call produces). OR inside a field (e.g. `players=2&players=3`), AND between fields.
`soft=<name>` marks a constraint as non-strict (boost instead of exclude), e.g. `soft=duration`.
"""

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger

from app.models.game_hit import GameHit
from app.rag.filters.search_filters import SearchFilters
from app.rag.retriever import GameRetriever

logger = get_logger(__name__)

router = APIRouter()
_retriever = GameRetriever()


def _range(lo, hi) -> dict | None:
    d = {k: v for k, v in (("min", lo), ("max", hi)) if v is not None}
    return d or None


@router.get("/search", response_model=list[GameHit])
def search(
    q: str = Query(..., description="free text, e.g. 'cooperative fantasy for two'"),
    k: int = Query(5, ge=1, le=20),
    players: list[int] = Query(default=[], description="supported player counts (OR), e.g. 2,3"),
    min_duration: int | None = Query(default=None),
    max_duration: int | None = Query(default=None),
    min_complexity: int | None = Query(default=None, description="complexity_level 1..5"),
    max_complexity: int | None = Query(default=None),
    max_age: int | None = Query(default=None, description="age_min <= this (e.g. for an 8-year-old)"),
    min_year: int | None = Query(default=None),
    max_year: int | None = Query(default=None),
    min_rating: float | None = Query(default=None),
    categoria: list[str] = Query(default=[]),
    marca: list[str] = Query(default=[]),
    exclude_expansions: bool = Query(default=False),
    soft: list[str] = Query(default=[], description="constraint names to treat as boost, not "
                            "exclude: players,duration,complexity,age,year,rating,categoria,marca"),
):
    # Assemble the per-field spec; only the fields the caller actually set end up in it.
    spec: dict[str, dict] = {}
    if players:
        spec["players"] = {"vals": players}
    if categoria:
        spec["categoria"] = {"vals": categoria}
    if marca:
        spec["marca"] = {"vals": marca}
    if (r := _range(min_duration, max_duration)):
        spec["duration"] = r
    if (r := _range(min_complexity, max_complexity)):
        spec["complexity"] = r
    if (r := _range(None, max_age)):
        spec["age"] = r
    if (r := _range(min_year, max_year)):
        spec["year"] = r
    if (r := _range(min_rating, None)):
        spec["rating"] = r
    if exclude_expansions:
        spec["expansions"] = {"val": False}
    for name in soft:
        if name in spec:
            spec[name]["soft"] = True

    try:
        filters = SearchFilters.from_dict(spec)
    except ValueError as e:
        logger.warning("search_rejected", query=q, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    return _retriever.search(q, k=k, filters=None if filters.is_empty() else filters)
