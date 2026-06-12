"""PilotedChat — the per-turn search budget (docs/idee.md §Q, arm B).

Purpose: lock the hard cap of MAX_SEARCHES_PER_TURN (2): a failed agent turn must have a
bounded cost — one search plus ONE retry, never a loop.
What it tests:
  - Two empty searches → exactly two retriever calls and ONE retry decision, even when the
    model keeps asking to retry; the turn ends on the honest no-match.
  - A successful first search never consults the retry step at all.
How: a retriever scripted to always return []; a retry queue that would happily retry forever.
"""

from app.chat.models.retry import RetryDecision


class TestBudget:
    def test_two_searches_max_then_honest_no_match(self, make_piloted):
        engine, retriever, _, retry, _ = make_piloted(
            results=[[]],
            decisions=[RetryDecision(query="ancora un tentativo"),
                       RetryDecision(query="e un altro")],
        )

        response = engine.reply("qualcosa che non esiste", session_id="s1")

        assert len(retriever.calls) == 2   # the budget, not the model, ends the loop
        assert len(retry.calls) == 1
        assert response.games == []
        assert engine.state("s1")["searches_used"] == 2

    def test_hits_on_first_search_never_consult_retry(self, make_piloted):
        engine, retriever, _, retry, _ = make_piloted()

        engine.reply("un gioco per stasera", session_id="s1")

        assert len(retriever.calls) == 1
        assert retry.calls == []
