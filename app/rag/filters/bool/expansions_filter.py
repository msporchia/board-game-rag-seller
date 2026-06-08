"""ExpansionsFilter: constrain the `is_expansion` flag.

To keep only base games (drop expansions) the caller sets `{"val": False}` → is_expansion == False.
"""

from app.rag.filters.bool.bool_filter import BoolFilter


class ExpansionsFilter(BoolFilter):
    field = "is_expansion"
