"""YearFilter: bound on the publication year (`year`)."""

from app.rag.filters.range.range_filter import RangeFilter


class YearFilter(RangeFilter):
    field = "year"
