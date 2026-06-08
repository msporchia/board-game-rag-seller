"""CategoriaFilter: match the game's `categoria` against an allowed set (OR)."""

from app.rag.filters.set.set_filter import SetFilter


class CategoriaFilter(SetFilter):
    field = "categoria"
