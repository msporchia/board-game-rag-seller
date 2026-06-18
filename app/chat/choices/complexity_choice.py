"""ComplexityChoice — "complessità bassa/media/alta" → a complexity range (BGG weight 1..5)."""

import re

from app.chat.choices.choice import Choice

# bassa → easy (<=2), media → 2..3, alta → heavy (>=3)
_BUCKETS = {"bassa": {"max": 2}, "media": {"min": 2, "max": 3}, "alta": {"min": 3}}


class ComplexityChoice(Choice):
    pattern = re.compile(r"\bcomplessit\w*\s+(bassa|media|alta)\b", re.IGNORECASE)

    def to_filter(self, match: re.Match) -> tuple[str, dict] | None:
        return ("complexity", _BUCKETS[match.group(1).lower()])
