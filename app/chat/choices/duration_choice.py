"""DurationChoice — "max N minuti" → duration upper bound."""

import re

from app.chat.choices.choice import Choice


class DurationChoice(Choice):
    pattern = re.compile(r"\bmax\s+(\d+)\s+min\w*", re.IGNORECASE)

    def to_filter(self, match: re.Match) -> tuple[str, dict] | None:
        n = int(match.group(1))
        return ("duration", {"max": n}) if n > 0 else None
