"""The forced QUICK_MATCH through the real graph: after 3 exchanges without a concrete
proposal the router must force QUICK_MATCH and that turn must do fresh retrieval
(docs/note.md transition rules; the pure `pick_strategy` rules live in `test_routing.py`).
"""

import pytest

pytest.importorskip("langgraph")

from app.chat.models.analysis import TurnAnalysis  # noqa: E402


class TestForcedQuickMatchThroughGraph:
    def test_fourth_guided_exchange_forces_quick_match_and_retrieves(self, make_graph):
        # A user that stays vague: low enthusiasm, undecided → GUIDED every turn.
        vague = [TurnAnalysis(enthusiasm="low", decisiveness="undecided", reply_style="long")]
        graph, retriever, _, _ = make_graph(analyses=vague)

        for msg in ("mah, non saprei", "boh", "non so decidermi"):
            graph.reply(msg, session_id="s")
        assert graph.state("s")["strategy"] == "GUIDED"
        # Only the FIRST guided turn retrieved (empty table); follow-ups reuse the same games.
        assert len(retriever.calls) == 1

        graph.reply("ancora dubbi", session_id="s")

        state = graph.state("s")
        assert state["strategy"] == "QUICK_MATCH"      # forced after 3 proposal-less exchanges
        assert len(retriever.calls) == 2               # ...and the forced turn re-retrieves
        assert state["turns_without_proposal"] == 0    # the proposal resets the counter
