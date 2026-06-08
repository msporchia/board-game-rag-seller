"""RangeFilter: a numeric lower/upper bound → Qdrant `Range(gte=min, lte=max)`.

Dict form `{"min": n, "max": n, "soft": bool}` — both bounds optional, at least one required.
A point MISSING the field never matches (same as Qdrant's range semantics): a game with unknown
duration is excluded by a hard duration bound, rather than silently passing.
"""

from typing import Optional

from qdrant_client import models as qm

from app.rag.filters.filter import Filter


class RangeFilter(Filter):
    def __init__(self, min: Optional[float] = None, max: Optional[float] = None, soft: bool = False):
        super().__init__(soft)
        self.min = min
        self.max = max

    def validate(self) -> None:
        if self.min is None and self.max is None:
            raise ValueError(f"{type(self).__name__}: at least one of 'min'/'max' is required")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(f"{type(self).__name__}: 'min' ({self.min}) > 'max' ({self.max})")

    def condition(self) -> qm.FieldCondition:
        return qm.FieldCondition(key=self.key, range=qm.Range(gte=self.min, lte=self.max))

    def matches(self, payload: dict) -> bool:
        v = payload.get(self.field)
        if v is None:
            return False
        if self.min is not None and v < self.min:
            return False
        if self.max is not None and v > self.max:
            return False
        return True
