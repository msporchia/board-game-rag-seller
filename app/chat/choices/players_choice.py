"""PlayersChoice — "per N giocatori" → players filter."""

import re

from app.chat.choices.choice import Choice


class PlayersChoice(Choice):
    pattern = re.compile(r"\bper\s+(\d+)\s+giocator\w*", re.IGNORECASE)

    def to_filter(self, match: re.Match) -> tuple[str, dict] | None:
        n = int(match.group(1))
        return ("players", {"vals": [n]}) if n >= 1 else None
