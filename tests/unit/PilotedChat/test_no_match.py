"""PilotedChat — the informed honest no-match (docs/idee.md §Q, arm B).

Purpose: lock that giving up is a DECISION made knowing the result count, and that every
give-up path lands on the same honest reply (the ChatAdvisor invariant, unchanged).
What it tests:
  - The model answers no_match=true → no second search, honest empty reply.
  - A retry decision with no query is a give-up, not a blank search.
  - The retry step failing (transport) degrades to the honest no-match, never a 500.
How: a retriever scripted to return []; RetryDecision variants per test.
"""

from app.chat.advisor import _NO_MATCH
from app.chat.models.retry import RetryDecision


class TestNoMatch:
    def test_no_match_decision_stops_the_searching(self, make_piloted):
        engine, retriever, _, _, _ = make_piloted(
            results=[[]], decisions=[RetryDecision(no_match=True)])

        response = engine.reply("avete Monopoly del 1936?", session_id="s1")

        assert len(retriever.calls) == 1
        assert response.games == []
        assert response.message == _NO_MATCH

    def test_retry_without_a_query_is_a_give_up(self, make_piloted):
        engine, retriever, _, _, _ = make_piloted(
            results=[[]], decisions=[RetryDecision(no_match=False, query="  ")])

        response = engine.reply("qualcosa di impossibile", session_id="s1")

        assert len(retriever.calls) == 1
        assert response.message == _NO_MATCH

    def test_retry_failure_degrades_to_honest_no_match(self, make_piloted):
        engine, retriever, _, _, _ = make_piloted(results=[[]], retry_raises=True)

        response = engine.reply("qualcosa di impossibile", session_id="s1")

        assert len(retriever.calls) == 1
        assert response.games == []
        assert response.message == _NO_MATCH
