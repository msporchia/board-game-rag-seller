"""DurationChoice — "max N minuti" → duration upper bound (tested in isolation)."""

from app.chat.choices.duration_choice import DurationChoice

_C = DurationChoice()


def _parse(text: str):
    match = _C.pattern.search(text)
    return _C.to_filter(match) if match else None


class TestDurationChoice:
    def test_parses_max_duration(self):
        assert _parse("max 60 minuti") == ("duration", {"max": 60})

    def test_zero_minutes_is_rejected(self):
        assert _parse("max 0 minuti") is None

    def test_unrelated_text_does_not_match(self):
        assert _parse("per 2 giocatori") is None
