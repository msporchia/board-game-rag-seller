"""PlayersChoice — "per N giocatori" → players filter (tested in isolation)."""

from app.chat.choices.players_choice import PlayersChoice

_C = PlayersChoice()


def _parse(text: str):
    match = _C.pattern.search(text)
    return _C.to_filter(match) if match else None


class TestPlayersChoice:
    def test_parses_player_count(self):
        assert _parse("per 2 giocatori") == ("players", {"vals": [2]})

    def test_case_insensitive(self):
        assert _parse("Per 4 Giocatori") == ("players", {"vals": [4]})

    def test_zero_players_is_rejected(self):
        assert _parse("per 0 giocatori") is None  # matches the shape, nonsense value → None

    def test_unrelated_text_does_not_match(self):
        assert _parse("Sorprendimi") is None
