"""RatingFilter: bound on the internal rating (`internal_rating`), e.g. {"min": 7}."""

from app.rag.filters.range.range_filter import RangeFilter


class RatingFilter(RangeFilter):
    field = "internal_rating"
