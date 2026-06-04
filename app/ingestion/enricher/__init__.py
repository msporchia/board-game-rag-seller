"""DATA enrichment pipeline (one file per enricher).

Stage: source → [EnrichmentPipeline] → serializer → vector store.
Production order (build_pipeline): Curator → Web → Synth → Compose(Rule).
(Extract/Augment/GapFill/Trim are stubs/experiments, not in the default chain.)

Public imports (compatibility: `from app.ingestion.enricher import X`).
"""

from app.ingestion.enricher.augment import AugmentEnricher
from app.ingestion.enricher.base import Enricher, EnrichmentPipeline, with_enriched
from app.ingestion.enricher.compose import RuleComposeEnricher
from app.ingestion.enricher.extract import ExtractEnricher
from app.ingestion.enricher.gapfill import GapFillEnricher
from app.ingestion.enricher.curator import CuratorEnricher
from app.ingestion.enricher.synth import SynthEnricher
from app.ingestion.enricher.trim import TrimEnricher
from app.ingestion.enricher.web import WebEnricher

__all__ = [
    "Enricher",
    "EnrichmentPipeline",
    "with_enriched",
    "TrimEnricher",
    "RuleComposeEnricher",
    "CuratorEnricher",
    "SynthEnricher",
    "ExtractEnricher",
    "WebEnricher",
    "AugmentEnricher",
    "GapFillEnricher",
]
