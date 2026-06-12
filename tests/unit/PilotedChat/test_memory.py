"""PilotedChat — session memory over the shared ChatState (docs/idee.md §Q, arm B).

Purpose: lock the lingua-franca side of arm B: history accumulates per session through the
same checkpointer mechanics as the pipeline, the intent step reads it, and every turn fetches
FRESH games (searching on fresh intent replaces the pipeline's re-retrieval skip-condition).
What it tests:
  - Turn 2's intent prompt carries turn 1's exchange (both the user and the bot line).
  - Every turn searches: two turns → two retriever calls, each with that turn's intent query.
  - Sessions are isolated: another session_id starts with a clean history.
How: scripted intent queue, default single-batch retriever.
"""

from app.chat.models.intent import SearchIntent


class TestMemory:
    def test_intent_reads_the_previous_exchange(self, make_piloted):
        engine, _, intent, _, _ = make_piloted(
            intents=[SearchIntent(query="gioco di carte"),
                     SearchIntent(query="gioco di carte fantascienza")])

        engine.reply("mi piacciono i giochi di carte", session_id="s1")
        engine.reply("a tema fantascienza", session_id="s1")

        assert "utente: mi piacciono i giochi di carte" in intent.calls[1]
        assert "bot: " in intent.calls[1]

    def test_every_turn_searches_with_fresh_intent(self, make_piloted):
        engine, retriever, _, _, _ = make_piloted(
            intents=[SearchIntent(query="prima"), SearchIntent(query="seconda")])

        engine.reply("primo turno", session_id="s1")
        engine.reply("secondo turno", session_id="s1")

        assert [c[0] for c in retriever.calls] == ["prima", "seconda"]

    def test_sessions_are_isolated(self, make_piloted):
        engine, _, intent, _, _ = make_piloted()

        engine.reply("messaggio della sessione uno", session_id="s1")
        engine.reply("ciao", session_id="s2")

        assert "(inizio conversazione)" in intent.calls[1]
        assert "sessione uno" not in intent.calls[1]
