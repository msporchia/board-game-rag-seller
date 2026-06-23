"""CuratorEnricher — the `cooperative` flag (SEL-142): LLM INFERENCE, with the catalog tag as the
only deterministic shortcut. The verdict is semantic (True/False/None), NOT a verbatim/keyword
match — a game that plays co-op without ever using the word is still caught.

These are deterministic UNIT tests (fake LLM): they verify the WIRING — how the curator routes a
given verdict onto the flag. Whether the PROMPT actually deduces the mode from a real description
is a separate, real-LLM check on real games in tests/e2e/enrichment/test_cooperative_inference.py.

HOW: fake LLM via `make_curator(content)`. The inference call expects `{"modalita": ...}`; the
extraction batches harmlessly ignore that JSON (no labels match), so one fake content drives the
bit under test. The co-op prompt is identifiable by the "MODALITÀ" marker.
"""

import json

from tests.factories.game import make_game

# means cooperative WITHOUT using the word — only inference (not a keyword hunt) can classify it
_COOP_NO_WORD = ("I giocatori uniscono le forze e affrontano insieme il morbo: "
                 "si vince o si perde tutti insieme.")


def _coop(modalita: str) -> str:
    """The JSON the inference LLM returns."""
    return json.dumps({"modalita": modalita})


class TestCuratorCooperative:
    def test_certain_tag_wins_without_inference(self, make_curator):
        """An explicit catalog co-op tag is certain data → True, and the inference LLM is never
        consulted (even though it would have said the opposite here)."""
        c = make_curator(_coop("competitivo"))
        out = c.enrich(make_game(tags=["Cooperativo"], description="qualcosa"))
        assert out.enriched.cooperative is True
        assert not any("MODALITÀ" in call for call in c._llm.calls)

    def test_inference_classifies_cooperative_without_the_word(self, make_curator):
        """INFERENCE, not keyword match: the description never says 'cooperativo', yet the model's
        verdict sets the flag True."""
        out = make_curator(_coop("cooperativo")).enrich(
            make_game(tags=[], description=_COOP_NO_WORD))
        assert out.enriched.cooperative is True

    def test_inference_classifies_competitive_as_false(self, make_curator):
        out = make_curator(_coop("competitivo")).enrich(make_game(
            tags=[], description="Ogni giocatore gioca per sé e cerca di battere gli avversari."))
        assert out.enriched.cooperative is False

    def test_inference_uncertain_stays_unknown(self, make_curator):
        out = make_curator(_coop("incerto")).enrich(
            make_game(tags=[], description="Un gioco di carte molto generico."))
        assert out.enriched.cooperative is None

    def test_inference_failure_stays_unknown(self, make_curator):
        """Unparseable model output → unknown, never a guessed verdict (SEL-142)."""
        out = make_curator("not-json {").enrich(make_game(tags=[], description="Un gioco."))
        assert out.enriched.cooperative is None

    def test_no_description_skips_inference(self, make_curator):
        c = make_curator(_coop("cooperativo"))
        out = c.enrich(make_game(tags=[], description=""))
        assert out.enriched.cooperative is None
        assert not any("MODALITÀ" in call for call in c._llm.calls)

    def test_tag_hidden_routes_through_inference_wiring(self, make_curator):
        """WIRING (deterministic, fake LLM): with the co-op tag stripped the verdict is no longer
        a shortcut, so the inference path drives the flag — here a faked 'cooperativo' sets True.
        This proves the plumbing only; whether the PROMPT actually deduces co-op from a real
        description is validated against real games in tests/e2e (test_cooperative_inference)."""
        hidden = make_game(tags=[], description="Si gioca tutti insieme contro il gioco.")
        assert hidden.enriched.cooperative is None  # tag stripped → unknown at construction
        out = make_curator(_coop("cooperativo")).enrich(hidden)
        assert out.enriched.cooperative is True
