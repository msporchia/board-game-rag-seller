"""AgeFilter: bound on the minimum recommended age (`age_min`).

`age_min` is the game's MINIMUM age, so "suitable for an 8-year-old" is `{"max": 8}` → age_min <= 8.
"""

from app.rag.filters.range.range_filter import RangeFilter


class AgeFilter(RangeFilter):
    field = "age_min"
