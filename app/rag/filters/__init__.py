"""Structured search filters (Phase 3, hybrid search).

Public surface re-exported so callers keep `from app.rag.filters import SearchFilters, rerank_soft`.
The individual filters live one-per-file under set/ range/ bool/ (see `filter.py` for the base).
"""

from app.rag.filters.rerank import SOFT_BOOST, rerank_soft
from app.rag.filters.search_filters import REGISTRY, SearchFilters, UnknownFilterError

__all__ = ["SearchFilters", "rerank_soft", "SOFT_BOOST", "REGISTRY", "UnknownFilterError"]
