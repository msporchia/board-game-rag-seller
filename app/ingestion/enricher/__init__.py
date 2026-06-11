"""DATA enrichment pipeline — one file per enricher, import what you need
(e.g. `from app.ingestion.enricher.web import WebEnricher`).

Stage: source → [pipeline.EnrichmentPipeline] → serializer → vector store.
Production order (ingester.build_pipeline): Curator → Web → Synth → Compose(Rule).
(Extract/Augment/GapFill/Trim are stubs/experiments, not in the default chain.)
"""
