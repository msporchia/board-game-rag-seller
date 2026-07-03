"""CuratorEnricher — the `cooperative` flag (SEL-142 + SEL-145): LLM INFERENCE, with the catalog
tag as the only deterministic shortcut, under the evidence discipline: the model's verdict
(either direction) counts ONLY with a quote the code re-validates verbatim in the description;
anything unproven degrades to the honest None. Rationale (SEL-145): the flag feeds a HARD
retrieval filter, so a wrong verdict in either direction is unacceptable while a None costs
nothing — the model is prompted to abstain and the code enforces the proof.

These are deterministic UNIT tests (fake LLM): they verify the WIRING — how the curator routes a
given (verdict, proof) pair onto the flag. Whether the PROMPT actually deduces the mode from a
real description is a separate, real-LLM check in tests/e2e/enrichment/test_cooperative_inference.py
(strict: zero wrong verdicts either direction — the SEL-109 gate).

HOW: fake LLM via `make_curator(content)`. The inference call expects `{"modalita", "prova"}`;
the extraction batches harmlessly ignore that JSON (no labels match), so one fake content drives
the bit under test. The co-op prompt is identifiable by the "MODALITÀ" marker.
"""

import json

from tests.factories.game import make_game

# means cooperative WITHOUT using the word — only inference (not a keyword hunt) can classify it
_COOP_NO_WORD = ("I giocatori uniscono le forze e affrontano insieme il morbo: "
                 "si vince o si perde tutti insieme.")


def _coop(modalita: str, prova: str = "") -> str:
    """The JSON the inference LLM returns."""
    return json.dumps({"modalita": modalita, "prova": prova})


class TestCuratorCooperative:
    def test_certain_tag_wins_without_inference(self, make_curator):
        """An explicit catalog co-op tag is certain data → True, and the inference LLM is never
        consulted (even though it would have said the opposite here)."""
        c = make_curator(_coop("competitivo", "si vince o si perde tutti insieme"))
        out = c.enrich(make_game(tags=["Cooperativo"], description="qualcosa"))
        assert out.enriched.cooperative is True
        assert not any("MODALITÀ" in call for call in c._llm.calls)

    def test_inferred_cooperative_is_capped_even_with_proof(self, make_curator):
        """SEL-145 strict gate: even a PROVEN inferred «cooperativo» is capped to None — the
        oracle run showed marketing can lie about team play (a verbatim quote proves the text
        says it, not that it is true). True comes only from the curated catalog signal."""
        out = make_curator(_coop("cooperativo", "si vince o si perde tutti insieme")).enrich(
            make_game(tags=[], description=_COOP_NO_WORD))
        assert out.enriched.cooperative is None

    def test_verdict_without_proof_degrades_to_unknown(self, make_curator):
        """SEL-145: a verdict with an empty proof is unproven → the honest None, never a guess."""
        out = make_curator(_coop("cooperativo")).enrich(
            make_game(tags=[], description=_COOP_NO_WORD))
        assert out.enriched.cooperative is None

    def test_verdict_with_fabricated_proof_degrades_to_unknown(self, make_curator):
        """SEL-145: the proof is re-validated in code — a quote that is NOT verbatim in the
        description proves nothing, whatever the model claims."""
        out = make_curator(_coop("cooperativo", "tutti contro il gioco, in squadra")).enrich(
            make_game(tags=[], description=_COOP_NO_WORD))
        assert out.enriched.cooperative is None

    def test_inference_classifies_competitive_as_false(self, make_curator):
        out = make_curator(_coop("competitivo", "cerca di battere gli avversari")).enrich(
            make_game(
                tags=[],
                description="Ogni giocatore gioca per sé e cerca di battere gli avversari."))
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
        c = make_curator(_coop("cooperativo", "qualunque"))
        out = c.enrich(make_game(tags=[], description=""))
        assert out.enriched.cooperative is None
        assert not any("MODALITÀ" in call for call in c._llm.calls)

    def test_proof_check_tolerates_case_and_whitespace_only(self, make_curator):
        """The verbatim check normalizes case and whitespace runs, nothing else — the same
        spirit as the extraction validation. Exercised on the False direction (the one that
        ships verdicts)."""
        out = make_curator(_coop("competitivo", "CERCA DI  battere\ngli avversari")).enrich(
            make_game(
                tags=[],
                description="Ogni giocatore gioca per sé e cerca di battere gli avversari."))
        assert out.enriched.cooperative is False
