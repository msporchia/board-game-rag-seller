"""ComplexityFilter: bound on weight/complexity (`complexity_level`, BGG scale 1..5)."""

from app.rag.filters.range.range_filter import RangeFilter


class ComplexityFilter(RangeFilter):
    field = "complexity_level"

    def validate(self) -> None:
        super().validate()
        for bound in (self.min, self.max):
            if bound is not None and not (1 <= bound <= 5):
                raise ValueError("ComplexityFilter: complexity_level is on the 1..5 BGG scale")
