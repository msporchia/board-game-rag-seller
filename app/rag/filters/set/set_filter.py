"""SetFilter: an OR over a set of allowed values → Qdrant `MatchAny`.

Covers both list payloads (e.g. the exploded `players` array — match = the lists intersect) and
scalar payloads (e.g. `categoria` — match = the value is in the set). The dict form is
`{"vals": [...], "soft": bool}`.
"""

from qdrant_client import models as qm

from app.rag.filters.filter import Filter


class SetFilter(Filter):
    def __init__(self, vals, soft: bool = False):
        super().__init__(soft)
        self.vals = list(vals)

    def validate(self) -> None:
        if not self.vals:
            raise ValueError(f"{type(self).__name__}: 'vals' must be non-empty")

    def condition(self) -> qm.FieldCondition:
        return qm.FieldCondition(key=self.key, match=qm.MatchAny(any=self.vals))

    def matches(self, payload: dict) -> bool:
        got = payload.get(self.field)
        if isinstance(got, list):
            return bool(set(got) & set(self.vals))
        return got in set(self.vals)
