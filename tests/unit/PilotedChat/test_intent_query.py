"""PilotedChat — the intent step (docs/idee.md §Q, arm B).

Purpose: lock "the model proposes, the code disposes" at the retrieval boundary.
What it tests:
  - The retrieval query is the MODEL's reformulation, never the user's verbatim text.
  - Model-declared constraints become real filters on the search (the structured side-channel
    that keeps the reformulation from losing the user's requirements).
  - Click-derived filters override the model's proposal on the same dimension and stay in the
    session spec, exactly like the pipeline (ClickParser + latest-wins, unchanged).
  - An intent failure degrades to the verbatim message (no constraints), never a 500.
How: scripted SearchIntent queue + a retriever that records every (query, k, filters) call.
"""

from app.chat.models.intent import SearchIntent


class TestIntentQuery:
    def test_retrieval_query_is_the_models_reformulation(self, make_piloted):
        engine, retriever, intent, _, _ = make_piloted(
            intents=[SearchIntent(query="gioco cooperativo per famiglie")])

        engine.reply("vorrei giocare tutti insieme contro il gioco", session_id="s1")

        assert retriever.calls == [("gioco cooperativo per famiglie", 5, None)]
        # The intent step saw the user's text; the retriever never did.
        assert "tutti insieme contro il gioco" in intent.calls[0]

    def test_model_constraints_become_filters_on_the_search(self, make_piloted):
        engine, retriever, _, _, _ = make_piloted(
            intents=[SearchIntent(query="party game", players=6, max_minutes=45,
                                  youngest_player_age=8)])

        engine.reply("siamo in sei, max tre quarti d'ora, c'è un bimbo di 8 anni",
                     session_id="s1")

        searched = engine.state("s1")["turn_searches"]
        assert searched[0]["filters"] == {"players": {"vals": [6]},
                                          "duration": {"max": 45},
                                          "age": {"max": 8}}
        assert retriever.calls[0][2] is not None  # a real SearchFilters reached the retriever

    def test_clicks_override_the_models_proposal_per_dimension(self, make_piloted):
        engine, _, _, _, _ = make_piloted(
            intents=[SearchIntent(query="gioco astratto", players=4)])

        engine.reply("qualcosa di astratto", choices=["per 2 giocatori"], session_id="s1")

        state = engine.state("s1")
        # The click wins the players dimension; the model keeps only what clicks don't cover.
        assert state["turn_searches"][0]["filters"]["players"] == {"vals": [2]}
        # The session spec records the CLICK (lingua franca with the pipeline), not the model.
        assert state["filters_spec"] == {"players": {"vals": [2]}}

    def test_intent_failure_degrades_to_the_verbatim_message(self, make_piloted):
        engine, retriever, _, _, _ = make_piloted(intent_raises=True)

        response = engine.reply("un gestionale pesante", session_id="s1")

        assert retriever.calls == [("un gestionale pesante", 5, None)]
        assert response.games  # the turn still produced a grounded reply

    def test_custom_policy_shapes_generation_not_the_intent_step(self, make_piloted):
        engine, _, intent, _, pitch = make_piloted(
            intents=[SearchIntent(query="gioco regalo per Natale")])

        engine.reply(
            "un regalo",
            session_id="s1",
            custom_policy=["christmas_sale", "assume_advanced"],
        )

        # Policies wrap retrieve/generate, not the intent step: the intent prompt stays clean.
        assert "saldi di Natale" not in intent.calls[0]
        # christmas_sale (around_generate) and assume_advanced (force_expertise) reach the pitch.
        assert "saldi di Natale" in pitch.calls[0]
        assert "livello di esperienza: advanced" in pitch.calls[0]
