"""AgeChoice — "dai N anni" → age cap (tested in isolation)."""

from app.chat.choices.age_choice import AgeChoice

_C = AgeChoice()


def _parse(text: str):
    match = _C.pattern.search(text)
    return _C.to_filter(match) if match else None


class TestAgeChoice:
    def test_parses_age(self):
        assert _parse("dai 8 anni") == ("age", {"max": 8})

    def test_da_without_i_also_matches(self):
        assert _parse("da 10 anni") == ("age", {"max": 10})

    def test_zero_is_rejected(self):
        assert _parse("dai 0 anni") is None
