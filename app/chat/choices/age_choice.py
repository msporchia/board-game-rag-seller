"""AgeChoice — "dai N anni" → age cap (a game suits an N-year-old when its min age <= N)."""

import re

from app.chat.choices.choice import Choice


class AgeChoice(Choice):
    pattern = re.compile(r"\bda[i]?\s+(\d+)\s+anni\b", re.IGNORECASE)

    def to_filter(self, match: re.Match) -> tuple[str, dict] | None:
        n = int(match.group(1))
        return ("age", {"max": n}) if n > 0 else None
