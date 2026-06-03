"""EnrichmentPipeline: applies the steps in order; empty is a no-op."""

from app.ingestion.enricher import EnrichmentPipeline, RuleComposeEnricher, TrimEnricher
from tests.factories import make_game


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
