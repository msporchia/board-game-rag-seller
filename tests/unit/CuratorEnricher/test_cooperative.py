"""CuratorEnricher — the `cooperative` flag (SEL-142): LLM INFERENCE, with the catalog tag as the
only deterministic shortcut. The verdict is semantic (True/False/None), NOT a verbatim/keyword
match — a game that plays co-op without ever using the word is still caught.

The "hide the data, check against the ORACLE" cross-test: the catalog co-op tag is ground truth;
we strip it and assert the inference recovers the verdict.

HOW: fake LLM via `make_curator(content)`. The inference call expects `{"modalita": ...}`; the
extraction batches harmlessly ignore that JSON (no labels match), so one fake content drives the
bit under test. The co-op prompt is identifiable by the "MODALITÀ" marker.
"""

import json
from pathlib import Path

import pytest

from tests.factories.game import make_game

FIXTURE = Path(__file__).parent / "fixtures" / "games.json"
_DTOS = json.loads(FIXTURE.read_text(encoding="utf-8"))
# the oracle: the games the catalog itself marks cooperative (the tag is ground truth)
COOP_DTOS = [d for d in _DTOS if any("cooperativ" in t.lower() for t in d.get("tags", []))]
COOP_IDS = [f"{d['id_product']}-{d['name'][:20]}" for d in COOP_DTOS]

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

    @pytest.mark.parametrize("dto", COOP_DTOS, ids=COOP_IDS)
    def test_recovered_from_inference_when_tag_hidden(self, make_curator, dto):
        """THE CROSS-TEST: blank the co-op tag (oracle = cooperative); with only the description
        left, the inference path recovers the verdict → matches the oracle."""
        desc = dto.get("description") or "Si gioca tutti insieme contro il gioco."
        hidden = make_game(tags=[], description=desc)  # the co-op tag stripped → unknown
        assert hidden.enriched.cooperative is None
        out = make_curator(_coop("cooperativo")).enrich(hidden)
        assert out.enriched.cooperative is True  # recovered → matches the oracle
