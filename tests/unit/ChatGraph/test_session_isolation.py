"""Session isolation — state keyed by session_id (thread_id) must NOT leak across different
session_ids (the within-session persistence lives in `test_memory.py`).
"""

import pytest

pytest.importorskip("langgraph")


class TestIsolationAcrossSessions:
    def test_filters_do_not_leak_between_sessions(self, make_graph):
        graph, _, _, _ = make_graph()

        graph.reply("per noi due", choices=["per 2 giocatori"], session_id="A")
        graph.reply("un gioco qualsiasi", session_id="B")

        assert graph.state("A")["filters_spec"] == {"players": {"vals": [2]}}
        assert not graph.state("B").get("filters_spec")

    def test_history_does_not_leak_between_sessions(self, make_graph):
        graph, _, _, _ = make_graph()

        graph.reply("messaggio di A", session_id="A")
        graph.reply("messaggio di B", session_id="B")

        assert "utente: messaggio di B" not in graph.state("A")["history"]
        assert "utente: messaggio di A" not in graph.state("B")["history"]
