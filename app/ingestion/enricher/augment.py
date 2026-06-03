"""AugmentEnricher: enriches a too-thin text (TODO)."""

from app.ingestion.enricher.base import Enricher
from app.models import GameDoc


class AugmentEnricher(Enricher):
    """GUARD: text too short / missing something key? → augment it (LLM)."""

    def enrich(self, game: GameDoc) -> GameDoc:
        raise NotImplementedError("AugmentEnricher: to be implemented (LLM)")
