"""WebEnricher — enrich() output wiring: where the verified facts land.

PURPOSE: the step must DUAL-WRITE the facts it recovered: into the structured `extracted` bag
(so `extracted` is the single complete fact-record — curator + web — that Synth consumes and the
store persists) AND into the description block (so the facts stay in embed_text even when Synth
is off). HOW: we isolate enrich() by feeding a known assessment (no network, no LLM); only the
merge logic is under examination.
"""

from tests.factories import make_game


def _assessment(game):
    return {"facts": {"ambientazione/tema": [{"value": "Toscana", "source": "goblins.net"}]},
            "sources": ["https://goblins.net/x"]}


class TestWebEnricherEnrich:
    def test_dual_writes_facts_to_extracted_and_description(self, make_web):
        w = make_web()
        w.assess = _assessment  # isolate enrich() from search/fetch/LLM
        g = make_game(id_product=3, description="Un gestionale.").model_copy(update={
            "missing_info": ["ambientazione/tema"],
            "extracted": {"genere": "gestionale"},  # a pre-existing curator fact
        })

        out = w.enrich(g)

        # structured bag: the curator key is preserved, the web fact is merged in
        assert out.extracted == {"genere": "gestionale", "ambientazione/tema": "Toscana"}
        # human-readable block still appended → the fact survives in embed_text without Synth
        assert "Toscana" in out.enriched.description
        # the now-recovered label leaves missing_info
        assert "ambientazione/tema" not in out.missing_info

    def test_no_facts_leaves_extracted_untouched(self, make_web):
        w = make_web()
        w.assess = lambda game: {"facts": {}, "sources": []}
        g = make_game(id_product=4).model_copy(update={
            "missing_info": ["durata"], "extracted": {"genere": "gestionale"}})

        out = w.enrich(g)

        assert out.extracted == {"genere": "gestionale"}  # unchanged
        assert out is g  # nothing verified online → the game is returned as-is

    def test_guard_skips_when_no_missing_info(self, make_web):
        w = make_web()
        g = make_game(id_product=5).model_copy(update={"extracted": {"genere": "gestionale"}})
        assert w.enrich(g) is g  # no gaps → no-op, extracted untouched
