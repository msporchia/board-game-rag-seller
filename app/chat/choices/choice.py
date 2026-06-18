"""Base class for one quick-reply CHOICE type (Phase 5: "a click becomes a new filter").

Each concrete choice (one per file) owns its own machine-parseable shape (`pattern`) and how to
turn a regex match into an effect — today a `SearchFilters` fragment `(name, params)`. It is a
CLASS, not a row in a flat table, precisely so a choice can GROW: a future strategic choice (one
that nudges a selling strategy or activates a policy, not just a filter) extends its own class
without touching the others, and each is unit-testable in isolation.

The parsing is DETERMINISTIC (regex, no LLM) because we control both ends — the pitch prompt
instructs the model to emit clicks in exactly these shapes, so a choice only has to recognize what
we ourselves generate. A captured-but-nonsensical value (e.g. "per 0 giocatori") returns None, so
the click degrades to a free-text leftover rather than a bad filter.
"""

import re
from abc import ABC, abstractmethod
from typing import ClassVar


class Choice(ABC):
    pattern: ClassVar[re.Pattern]

    @abstractmethod
    def to_filter(self, match: re.Match) -> tuple[str, dict] | None:
        """The `(filter_name, params)` SearchFilters fragment this click contributes, or None if
        the captured value is nonsense (→ the click becomes a leftover)."""
