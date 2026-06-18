"""ExpansionsChoice — "senza espansioni" → base-game-only filter (tested in isolation)."""

from app.chat.choices.expansions_choice import ExpansionsChoice

_C = ExpansionsChoice()


def _parse(text: str):
    match = _C.pattern.search(text)
    return _C.to_filter(match) if match else None


class TestExpansionsChoice:
    def test_parses_no_expansions(self):
        assert _parse("senza espansioni") == ("expansions", {"val": False})

    def test_unrelated_text_does_not_match(self):
        assert _parse("con espansioni") is None
