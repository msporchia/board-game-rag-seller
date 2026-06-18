"""ExpansionsChoice — "senza espansioni" → base-game-only filter."""

import re

from app.chat.choices.choice import Choice


class ExpansionsChoice(Choice):
    pattern = re.compile(r"\bsenza\s+espansioni\b", re.IGNORECASE)

    def to_filter(self, match: re.Match) -> tuple[str, dict] | None:
        return ("expansions", {"val": False})
