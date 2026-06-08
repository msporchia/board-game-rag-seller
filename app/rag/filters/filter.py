"""Base class for a single structured search constraint (Phase 3, hybrid search).

Each concrete filter (one per file, grouped by type under set/ range/ bool/) knows three things
about its own field, so the container does not branch on type:
- `validate()` — sanity-checks its values, raising `ValueError` on nonsense (the point of the
  class hierarchy: bad input fails loud and early instead of slipping through);
- `condition()` — the Qdrant `FieldCondition` for the HARD pre-filter (excludes non-matches);
- `matches(payload)` — the Python predicate used in SOFT mode (boost, not exclude).

`field` is the payload key (e.g. "players"). langchain_qdrant nests the document metadata under a
"metadata" payload key, so the Qdrant condition addresses it as "metadata.<field>" (`key`), while
`matches` runs on `doc.metadata`, which LangChain has already un-nested back to the top level.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from qdrant_client import models as qm

_PAYLOAD_PREFIX = "metadata."


class Filter(ABC):
    field: ClassVar[str]

    def __init__(self, soft: bool = False):
        self.soft = soft

    @property
    def key(self) -> str:
        """Qdrant payload path (langchain nests metadata under 'metadata.')."""
        return _PAYLOAD_PREFIX + self.field

    def validate(self) -> None:
        """Sanity-check the values; override in subclasses. Default: no-op."""

    @abstractmethod
    def condition(self) -> qm.FieldCondition:
        """The Qdrant condition for the hard pre-filter."""

    @abstractmethod
    def matches(self, payload: dict) -> bool:
        """Whether a point's (un-nested) payload satisfies this constraint (soft mode)."""
