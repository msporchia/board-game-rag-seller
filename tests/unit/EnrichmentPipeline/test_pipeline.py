"""EnrichmentPipeline: applies the steps in order; empty is a no-op."""

from app.ingestion.enricher.compose import RuleComposeEnricher
from app.ingestion.enricher.pipeline import EnrichmentPipeline
from app.ingestion.enricher.trim import TrimEnricher
from tests.factories.game import make_game


class TestEnrichmentPipeline:
    def test_applies_steps_in_order(self):
        long = "Frase. " * 200
        full = RuleComposeEnricher().enrich(make_game(description=long)).embed_text
        trimmed = EnrichmentPipeline([TrimEnricher(120), RuleComposeEnricher()]).run(
            make_game(description=long)
        ).embed_text
        assert len(trimmed) < len(full)  # the upstream trim shortens the composed text downstream

    def test_empty_pipeline_is_noop(self):
        g = make_game()
        assert EnrichmentPipeline().run(g) is g
