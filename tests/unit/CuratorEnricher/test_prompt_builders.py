"""CuratorEnricher — PURE prompt-building function.

PURPOSE: the prompt is the Curator's lever; its parts must be verified deterministically.
WHAT IT TESTS:
  - `_prompt`: no CERTAIN DATA, only DESCRIPTION; `{citazione, valore_normalizzato}` schema;
    contains EXACTLY the passed labels (dynamic list).
HOW: direct method calls (no LLM).
"""

from app.ingestion.enricher.curator import CuratorEnricher


class TestCuratorPromptBuilders:
    def test_prompt_is_description_only_citation_based(self, make_curator):
        """The reduced prompt: no CERTAIN DATA, only DESCRIPTION. The LLM produces
        `{citazione, valore_normalizzato}` per label. The VERBATIM quote stays the
        anti-fabrication invariant, validated downstream by the code."""
        labels = ["ambientazione/tema", "genere", "a chi è adatto"]
        prompt = CuratorEnricher._prompt(labels, "una descrizione di prova")
        assert "ETICHETTE" in prompt
        assert "VERBATIM" in prompt
        assert "DESCRIZIONE" in prompt
        # 2-field per-label schema (no more "dove")
        assert "citazione" in prompt
        assert "valore_normalizzato" in prompt
        # no CERTAIN DATA in the prompt
        assert "DATI CERTI" not in prompt and "DATI_CERTI" not in prompt
        assert "Giocatori:" not in prompt
        # no synthesis here
        assert "SINTESI" not in prompt
        assert "\"sintesi\"" not in prompt
        # only the passed labels are in the prompt (dynamic list)
        for lab in labels:
            assert f"- {lab}" in prompt
        assert "- numero giocatori" not in prompt
