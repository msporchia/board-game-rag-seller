"""SearchFilters: a bag of `Filter` objects, built from the dict an LLM tool-call produces.

The input is flat-per-field, e.g.:

    SearchFilters.from_dict({
        "players":    {"vals": [2, 3], "soft": True},
        "duration":   {"max": 60},
        "complexity": {"min": 2, "max": 3},
        "expansions": {"val": False},
    })

`from_dict` looks each name up in `REGISTRY`, instantiates the matching `Filter` with the params,
and calls `validate()` — an unknown name or nonsensical value fails loud and early. The container
itself does NOT branch on filter type: it just asks each filter for its hard `condition()` or its
soft `matches` predicate. Rule: OR inside a field (the filter's own values), AND between fields
(the `must` list).
"""

from typing import Optional

from qdrant_client import models as qm

from app.rag.filters.errors import UnknownFilterError
from app.rag.filters.bool.cooperative_filter import CooperativeFilter
from app.rag.filters.bool.expansions_filter import ExpansionsFilter
from app.rag.filters.filter import Filter
from app.rag.filters.range.age_filter import AgeFilter
from app.rag.filters.range.complexity_filter import ComplexityFilter
from app.rag.filters.range.duration_filter import DurationFilter
from app.rag.filters.range.rating_filter import RatingFilter
from app.rag.filters.range.year_filter import YearFilter
from app.rag.filters.set.categoria_filter import CategoriaFilter
from app.rag.filters.set.marca_filter import MarcaFilter
from app.rag.filters.set.players_filter import PlayersFilter

# name (as used in the tool-call / API) → concrete Filter class
REGISTRY: dict[str, type[Filter]] = {
    "players": PlayersFilter,
    "categoria": CategoriaFilter,
    "marca": MarcaFilter,
    "duration": DurationFilter,
    "complexity": ComplexityFilter,
    "age": AgeFilter,
    "year": YearFilter,
    "rating": RatingFilter,
    "expansions": ExpansionsFilter,
    "cooperative": CooperativeFilter,
}


class SearchFilters:
    def __init__(self, filters: list[Filter]):
        self.filters = filters

    @classmethod
    def from_dict(cls, spec: Optional[dict]) -> "SearchFilters":
        filters: list[Filter] = []
        for name, params in (spec or {}).items():
            try:
                klass = REGISTRY[name]
            except KeyError:
                raise UnknownFilterError(
                    f"unknown filter '{name}'; known: {sorted(REGISTRY)}"
                ) from None
            f = klass(**params)   # params keys must match the filter's constructor (vals/min/max/val/soft)
            f.validate()
            filters.append(f)
        return cls(filters)

    def hard_filter(self) -> Optional[qm.Filter]:
        """Qdrant pre-filter for the strict constraints (everything not marked soft)."""
        must = [f.condition() for f in self.filters if not f.soft]
        return qm.Filter(must=must) if must else None

    def soft_predicates(self) -> list:
        """Payload predicates for the soft constraints (used to boost, not exclude)."""
        return [f.matches for f in self.filters if f.soft]

    def is_empty(self) -> bool:
        return not self.filters
