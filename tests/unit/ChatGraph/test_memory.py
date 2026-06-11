"""Session memory — the checkpointer-backed state, keyed by session_id (thread_id).

Purpose: lock that state PERSISTS across turns of the same session (filters accumulate
per-field, history grows with both sides of the exchange). In-memory checkpointer: persistence
semantics, not the sqlite file, are under test. Cross-session isolation lives in
`test_session_isolation.py`.
"""

import pytest

pytest.importorskip("langgraph")


class TestMemoryWithinASession:
    def test_filters_accumulate_across_turns(self, make_graph):
        graph, retriever, _, _ = make_graph()

        graph.reply("un cooperativo", choices=["per 2 giocatori"], session_id="s")
        graph.reply("qualcosa di breve", choices=["max 60 minuti"], session_id="s")

        # The session remembers BOTH constraints...
        assert graph.state("s")["filters_spec"] == {
            "players": {"vals": [2]}, "duration": {"max": 60},
        }
        # ...and the second search applied both (players + duration_min payload fields).
        _, _, filters = retriever.calls[1]
        assert {f.field for f in filters.filters} == {"players", "duration_min"}

    def test_latest_click_on_a_dimension_wins(self, make_graph):
        graph, _, _, _ = make_graph()

        graph.reply("un gioco", choices=["per 2 giocatori"], session_id="s")
        graph.reply("anzi siamo di più", choices=["per 4 giocatori"], session_id="s")

        assert graph.state("s")["filters_spec"]["players"] == {"vals": [4]}

    def test_history_keeps_both_sides_of_the_exchange(self, make_graph):
        graph, _, _, _ = make_graph()

        graph.reply("primo messaggio", session_id="s")
        graph.reply("secondo messaggio", session_id="s")

        history = graph.state("s")["history"]
        assert "utente: primo messaggio" in history
        assert "utente: secondo messaggio" in history
        assert sum(1 for line in history if line.startswith("bot: ")) == 2
