"""ClickParser — quick-reply clicks → SearchFilters fragment + leftovers.

Purpose: lock the parser's own logic (recognize / leftover / latest-wins / mixed) and that the
fragments build real `SearchFilters`. The per-choice recognition lives in each choice's own test.
"""

from app.chat.choices.parser import ClickParser
from app.chat.choices.players_choice import PlayersChoice
from app.rag.filters.search_filters import SearchFilters

_P = ClickParser()


class TestParse:
    def test_recognized_click_becomes_a_spec_fragment(self):
        assert _P.parse(["per 2 giocatori"]) == ({"players": {"vals": [2]}}, [])

    def test_free_text_is_a_leftover_not_a_drop(self):
        assert _P.parse(["Sorprendimi"]) == ({}, ["Sorprendimi"])

    def test_latest_click_on_a_dimension_wins(self):
        assert _P.parse(["per 2 giocatori", "per 4 giocatori"]) == ({"players": {"vals": [4]}}, [])

    def test_mixed_clicks_split_into_spec_and_leftovers(self):
        spec, leftovers = _P.parse(["per 2 giocatori", "Sorprendimi", "max 60 minuti"])
        assert spec == {"players": {"vals": [2]}, "duration": {"max": 60}}
        assert leftovers == ["Sorprendimi"]

    def test_fragments_build_real_search_filters(self):
        spec, _ = _P.parse(["per 3 giocatori", "max 90 minuti", "dai 10 anni",
                            "senza espansioni", "complessità media"])
        assert len(SearchFilters.from_dict(spec).filters) == 5

    def test_choice_set_is_injectable(self):
        only_players = ClickParser(choices=[PlayersChoice()])
        # with only PlayersChoice registered, a duration click is unrecognized → leftover
        assert only_players.parse(["max 60 minuti"]) == ({}, ["max 60 minuti"])
