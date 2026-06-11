"""CuratorEnricher — `assess()` validation: the key INVARIANT is that no fabricated quote
survives. The LLM answers with {citazione, valore_normalizzato} per label; `assess()` checks the
quote VERBATIM against the description and degrades to `mancanti` anything not verifiable.

HOW: fake LLM via `make_curator(payload)` + hand-built games (`make_game`).
"""

from tests.factories.game import make_game


class TestCuratorAssessValidation:
    """The key INVARIANT: no fabricated quote survives."""

    def test_fabricated_citation_degrades_to_mancanti(self, make_curator, per_label):
        """The LLM quotes "mitologia greca" but the desc doesn't say it → degrade to mancanti."""
        payload = per_label(**{
            "ambientazione/tema": {"citazione": "mitologia greca",
                                    "valore_normalizzato": "greco"},   # FABRICATED
        })
        g = make_game(description="Un gioco generico senza dettagli.")
        a = make_curator(payload).assess(g)
        assert "ambientazione/tema" in a["mancanti"]
        assert "ambientazione/tema" not in a["presenti"]
        assert "ambientazione/tema" not in a["estratti"]

    def test_valid_text_citation_goes_to_presenti_and_estratti(self, make_curator, per_label):
        """VERBATIM quote in the description → present + value in estratti."""
        payload = per_label(**{
            "ambientazione/tema": {"citazione": "mitologia greca",
                                    "valore_normalizzato": "mitologia greca"},
        })
        g = make_game(description="Un gioco di mitologia greca antica.")
        a = make_curator(payload).assess(g)
        assert "ambientazione/tema" in a["presenti"]
        assert a["estratti"]["ambientazione/tema"] == "mitologia greca"

    def test_nessuno_value_goes_to_mancanti(self, make_curator, per_label):
        """`valore_normalizzato: "NESSUNO"` → label in mancanti, nothing in estratti."""
        payload = per_label(**{
            "ambientazione/tema": {"citazione": "", "valore_normalizzato": "NESSUNO"},
        })
        a = make_curator(payload).assess(make_game(description="qualcosa"))
        assert "ambientazione/tema" in a["mancanti"]
        assert "ambientazione/tema" not in a["estratti"]

    def test_fallback_to_citation_when_value_empty(self, make_curator, per_label):
        """If the LLM leaves `valore_normalizzato=""` but quotes a valid passage, we use the
        quote as the value (better something quoted than nothing)."""
        payload = per_label(**{
            "ambientazione/tema": {"citazione": "mitologia greca", "valore_normalizzato": ""},
        })
        g = make_game(description="Mitologia greca antica.")
        a = make_curator(payload).assess(g)
        assert a["estratti"]["ambientazione/tema"] == "mitologia greca"

    def test_meccaniche_text_value_is_split_into_list(self, make_curator, per_label):
        """For 'meccaniche principali' the extracted string becomes a LIST."""
        payload = per_label(**{
            "meccaniche principali": {"citazione": "cooperativo, lancio di dadi",
                                       "valore_normalizzato": "Cooperativo, Lancio di dadi"},
        })
        g = make_game(description="cooperativo, lancio di dadi", tags=[])
        a = make_curator(payload).assess(g)
        assert a["estratti"]["meccaniche principali"] == ["Cooperativo", "Lancio di dadi"]
