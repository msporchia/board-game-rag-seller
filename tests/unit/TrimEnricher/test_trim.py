"""TrimEnricher — FAILSAFE on description length.

PURPOSE: verify the behavior of the safety cap, not the quality of the cut.
WHAT IT TESTS: (a) above threshold → reduces to the first sentences and does NOT touch the
hard-truth `original`; (b) below threshold → no-op (the guard leaves the text intact); (c) the
DEFAULT is a high threshold (~1000) → a normal description passes through and it only fires on
an abnormal one (cost control).
HOW: deterministic synthetic inputs, no Ollama.
"""

from app.ingestion.enricher.trim import TrimEnricher
from tests.factories.game import make_game


class TestTrimEnricher:
    def test_shortens_enriched_and_keeps_original(self):
        """Above threshold: enriched shortened, original unchanged."""
        long = "Frase di prova. " * 100  # ~1600 chars
        g = make_game(description=long)
        out = TrimEnricher(max_chars=200).enrich(g)
        assert len(out.enriched.description) <= 240   # ~max + last sentence
        assert out.original.description == long        # hard-truth intact

    def test_guard_leaves_short_description(self):
        """Below threshold: no-op."""
        g = make_game(description="Corta.")
        out = TrimEnricher(max_chars=200).enrich(g)
        assert out.enriched.description == "Corta."

    def test_default_passes_normal_description(self):
        """Failsafe: a normal-length description (< default ~1000) is not touched."""
        normal = "Frase di prova. " * 50  # ~800 chars
        out = TrimEnricher().enrich(make_game(description=normal))
        assert out.enriched.description == normal

    def test_default_caps_obscene_description(self):
        """Failsafe: an abnormal description is brought back within ~1000 chars (cost control)."""
        obscene = "Parola lunga. " * 500  # ~7000 chars
        out = TrimEnricher().enrich(make_game(description=obscene))
        assert len(out.enriched.description) <= 1100
        assert out.original.description == obscene  # hard-truth intact
