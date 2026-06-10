"""Quick-reply clicks → SearchFilters fragments ("a click becomes a new filter").

Purpose: lock the deterministic parser (the machine-parseable shapes WE instruct the pitch LLM
to generate), the graceful leftover path for free-form clicks, and — through the graph — that a
click reaches retrieval as a real structured filter, no longer folded into the query string.
The parser tests do not need langgraph; the graph-level ones use the shared fixture.
"""

from app.chat.choices import parse_choices
from app.rag.filters import SearchFilters


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


class TestClicksThroughGraph:
    def test_click_becomes_a_filter_not_query_text(self, make_graph):
        graph, retriever, _, _ = make_graph()

        graph.reply("un gioco cooperativo", choices=["per 2 giocatori"], session_id="s")

        query, _, filters = retriever.calls[0]
        assert "per 2 giocatori" not in query            # no longer folded into the query
        players = [f for f in filters.filters if f.field == "players"]
        assert players and players[0].vals == [2]        # ...it is a real structured constraint

    def test_unparsed_click_still_reaches_the_query(self, make_graph):
        graph, retriever, _, _ = make_graph()

        graph.reply("un gioco", choices=["Sorprendimi"], session_id="s")

        query, _, filters = retriever.calls[0]
        assert "Sorprendimi" in query                    # graceful Phase 4-style degradation
        assert filters is None
