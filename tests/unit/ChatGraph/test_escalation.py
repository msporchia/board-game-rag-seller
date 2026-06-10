"""Model tiering — the escalation contract (docs/note.md "Model tiering").

Purpose: lock the MECHANISM, not any paid model: when the analyze step sets `escalate=true`,
the generate step must run on the strong LLM (and only then); the response still flows through
the same grounded pitch path.
"""

import pytest

pytest.importorskip("langgraph")

from app.chat.models import ChatRecommendation, ChatReply, TurnAnalysis  # noqa: E402


class TestEscalation:
    def test_escalate_true_switches_generate_to_the_strong_model(self, make_graph):
        wants_to_buy = [TurnAnalysis(
            decisiveness="decided", escalate=True,
            escalation_reason="budget e numero di giocatori già definiti", confidence=0.9,
        )]
        graph, _, gen, strong = make_graph(
            analyses=wants_to_buy,
            strong_reply=ChatReply(
                intro="Risposta dal modello forte.",
                recommendations=[ChatRecommendation(id=1, pitch="G1 è la scelta giusta.")],
            ),
        )

        res = graph.reply("ho 50 euro, siamo in 4, cosa prendo?", session_id="s")

        assert strong.calls and not gen.calls       # the strong model generated, not the default
        assert res.message == "Risposta dal modello forte. G1 è la scelta giusta."
        assert [g.id_product for g in res.games] == [1]  # grounding still applies on this path

    def test_no_escalation_stays_on_the_default_model(self, make_graph):
        graph, _, gen, strong = make_graph()  # default analysis: escalate=False

        graph.reply("un gioco da fare in famiglia", session_id="s")

        assert gen.calls and not strong.calls

    def test_escalation_is_per_turn_analysis(self, make_graph):
        # Turn 1 escalates, turn 2 does not → the flag follows the analysis, it does not stick.
        analyses = [
            TurnAnalysis(escalate=True, escalation_reason="complex ask", confidence=0.8),
            TurnAnalysis(escalate=False),
        ]
        graph, _, gen, strong = make_graph(analyses=analyses)

        graph.reply("primo turno", session_id="s")
        graph.reply("secondo turno", session_id="s")

        assert len(strong.calls) == 1
        assert len(gen.calls) == 1
