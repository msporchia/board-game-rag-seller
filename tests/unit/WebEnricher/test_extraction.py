"""WebEnricher — EXTRACTION with verification (the anti-hallucination invariant).

PURPOSE: it's the step's safety core — online you risk inventions, so a fact is kept ONLY if
it is provably in the source text.
WHAT IT TESTS: `_judge_extract` keeps a fact only if its QUOTE is verbatim in the text; it
discards everything if the quote is missing, if the page isn't about the game, if it isn't a
serious source, if the info wasn't requested, or if the LLM doesn't reply with JSON.
HOW: fixed text + a FAKE LLM response (we control what the model "would say") → we observe only
the validation; no network (conftest).
"""

import json


class TestWebEnricherExtraction:
    def test_keeps_fact_with_verifiable_quote(self, make_web):
        """Quote present in the text → fact kept."""
        text = "Viticulture è ambientato in Toscana, tra i vigneti."
        payload = {"is_this_game": True, "is_serious": True,
                   "found": {"ambientazione": {"value": "Toscana", "quote": "ambientato in Toscana"}}}
        out = make_web(json.dumps(payload))._judge_extract("Viticulture", ["ambientazione"], text)
        assert out == {"ambientazione": {"value": "Toscana", "quote": "ambientato in Toscana"}}

    def test_discards_fact_when_quote_not_in_text(self, make_web):
        """Quote absent from the text → fact discarded (anti-hallucination)."""
        text = "Una pagina che non dice nulla di utile sul gioco."
        payload = {"is_this_game": True, "is_serious": True,
                   "found": {"ambientazione": {"value": "Toscana", "quote": "ambientato in Toscana"}}}
        out = make_web(json.dumps(payload))._judge_extract("Viticulture", ["ambientazione"], text)
        assert out == {}

    def test_discards_when_not_this_game(self, make_web):
        """The page isn't about the game → no extraction."""
        text = "ambientato in Toscana"
        payload = {"is_this_game": False, "is_serious": True,
                   "found": {"ambientazione": {"value": "x", "quote": "ambientato in Toscana"}}}
        out = make_web(json.dumps(payload))._judge_extract("Viticulture", ["ambientazione"], text)
        assert out == {}

    def test_discards_when_not_serious(self, make_web):
        """Non-serious source (e.g. a product listing) → no extraction."""
        text = "ambientato in Toscana"
        payload = {"is_this_game": True, "is_serious": False,
                   "found": {"ambientazione": {"value": "x", "quote": "ambientato in Toscana"}}}
        out = make_web(json.dumps(payload))._judge_extract("Viticulture", ["ambientazione"], text)
        assert out == {}

    def test_ignores_info_not_requested(self, make_web):
        """An info outside the requested-missing ones is ignored."""
        text = "ambientato in Toscana"
        payload = {"is_this_game": True, "is_serious": True,
                   "found": {"durata": {"value": "60", "quote": "ambientato in Toscana"}}}
        out = make_web(json.dumps(payload))._judge_extract("Viticulture", ["ambientazione"], text)
        assert out == {}

    def test_parse_error_returns_empty(self, make_web):
        """Non-JSON LLM output → no fact (fail-safe)."""
        out = make_web("non-json {")._judge_extract("Viticulture", ["ambientazione"], "testo")
        assert out == {}
