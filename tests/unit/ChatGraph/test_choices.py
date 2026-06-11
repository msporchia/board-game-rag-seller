"""Quick-reply clicks → SearchFilters fragments ("a click becomes a new filter").

Purpose: lock the deterministic parser (the machine-parseable shapes WE instruct the pitch LLM
to generate) and the graceful leftover path for free-form clicks. No langgraph needed here;
the graph-level click tests live in `test_clicks_through_graph.py`.
"""

from app.chat.choices import parse_choices
from app.rag.filters.search_filters import SearchFilters


class TestParseChoices:
    def test_players_click(self):
        assert parse_choices(["per 2 giocatori"]) == ({"players": {"vals": [2]}}, [])

    def test_duration_click(self):
        assert parse_choices(["max 60 minuti"]) == ({"duration": {"max": 60}}, [])

    def test_age_click(self):
        assert parse_choices(["dai 8 anni"]) == ({"age": {"max": 8}}, [])

    def test_expansions_click(self):
        assert parse_choices(["senza espansioni"]) == ({"expansions": {"val": False}}, [])

    def test_complexity_click(self):
        assert parse_choices(["complessità bassa"]) == ({"complexity": {"max": 2}}, [])

    def test_case_insensitive(self):
        spec, leftovers = parse_choices(["Per 2 Giocatori"])
        assert spec == {"players": {"vals": [2]}} and leftovers == []

    def test_free_text_is_a_leftover_not_a_drop(self):
        assert parse_choices(["Sorprendimi"]) == ({}, ["Sorprendimi"])

    def test_nonsense_value_is_a_leftover(self):
        # "per 0 giocatori" matches the shape but is not a valid constraint.
        assert parse_choices(["per 0 giocatori"]) == ({}, ["per 0 giocatori"])

    def test_mixed_clicks(self):
        spec, leftovers = parse_choices(["per 2 giocatori", "Sorprendimi", "max 60 minuti"])
        assert spec == {"players": {"vals": [2]}, "duration": {"max": 60}}
        assert leftovers == ["Sorprendimi"]

    def test_specs_build_real_search_filters(self):
        # The fragments must be valid against the real filter REGISTRY (validate() included).
        spec, _ = parse_choices(["per 3 giocatori", "max 90 minuti", "dai 10 anni",
                                 "senza espansioni", "complessità media"])
        filters = SearchFilters.from_dict(spec)
        assert len(filters.filters) == 5
