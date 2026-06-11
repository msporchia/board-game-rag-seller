"""Through the graph: a click reaches retrieval as a real structured filter, no longer folded
into the query string — and an unparsed click still degrades gracefully into the query
(the parser itself is locked in `test_choices.py`).
"""

import pytest

pytest.importorskip("langgraph")


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
