"""PilotedChat — the explicit zero-result retry (docs/idee.md §Q, arm B).

Purpose: lock the informed retry loop — the model is TOLD the search came back empty and its
second query drives the second (and last) fetch.
What it tests:
  - Zero hits → one retry: the retry prompt carries the failed query, the new query reaches
    the retriever, and the reply is grounded over the SECOND search's results.
  - The model's own proposed constraints are dropped on retry (the likeliest culprit) while
    click filters survive — the retry cannot bypass the customer's explicit choices.
How: a retriever scripted to return [] first, games second; scripted RetryDecision queue.
"""

from app.chat.models.intent import SearchIntent
from app.chat.models.recommendation import ChatRecommendation
from app.chat.models.reply import ChatReply
from app.chat.models.retry import RetryDecision
from tests.unit.PilotedChat.fakes import make_hit


class TestRetry:
    def test_zero_hits_triggers_one_informed_retry(self, make_piloted):
        hits = [make_hit(i, f"G{i}") for i in (1, 2, 3)]
        engine, retriever, _, retry, _ = make_piloted(
            results=[[], hits],
            intents=[SearchIntent(query="prima query")],
            decisions=[RetryDecision(query="seconda query")],
            reply=ChatReply(intro="Ecco!", recommendations=[
                ChatRecommendation(id=1, pitch="G1 fa per voi.")]),
        )

        response = engine.reply("cerco qualcosa di introvabile", session_id="s1")

        # The retry step was informed of the exact failed query, then its query searched.
        assert "prima query" in retry.calls[0]
        assert [c[0] for c in retriever.calls] == ["prima query", "seconda query"]
        # The reply is grounded over the second search's hits.
        assert [g.id_product for g in response.games] == [1]
        assert [s["n_hits"] for s in engine.state("s1")["turn_searches"]] == [0, 3]

    def test_retry_drops_model_constraints_but_keeps_clicks(self, make_piloted):
        hits = [make_hit(1, "G1")]
        engine, _, _, _, _ = make_piloted(
            results=[[], hits],
            intents=[SearchIntent(query="prima query", players=7)],
            decisions=[RetryDecision(query="seconda query")],
            reply=ChatReply(recommendations=[ChatRecommendation(id=1, pitch="G1.")]),
        )

        engine.reply("per il nostro gruppo", choices=["max 30 minuti"], session_id="s1")

        first, second = engine.state("s1")["turn_searches"]
        assert first["filters"] == {"players": {"vals": [7]}, "duration": {"max": 30}}
        # Retry: the model's players guess is gone, the customer's click is not.
        assert second["filters"] == {"duration": {"max": 30}}
