"""MarcaFilter: match the game's `marca` (publisher) against an allowed set (OR)."""

from app.rag.filters.set.set_filter import SetFilter


class MarcaFilter(SetFilter):
    field = "marca"
