"""BoolFilter: exact boolean match on a payload flag → Qdrant `MatchValue`.

Dict form `{"val": bool, "soft": bool}`.
"""

from qdrant_client import models as qm

from app.rag.filters.filter import Filter


class BoolFilter(Filter):
    def __init__(self, val: bool, soft: bool = False):
        super().__init__(soft)
        self.val = val

    def validate(self) -> None:
        if not isinstance(self.val, bool):
            raise ValueError(f"{type(self).__name__}: 'val' must be a boolean")

    def condition(self) -> qm.FieldCondition:
        return qm.FieldCondition(key=self.key, match=qm.MatchValue(value=self.val))

    def matches(self, payload: dict) -> bool:
        return payload.get(self.field) is self.val
