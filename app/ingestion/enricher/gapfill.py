"""GapFillEnricher: generates sensible values for the still-missing fields (TODO)."""

from app.ingestion.enricher.enricher import Enricher
from app.models.game_doc import GameDoc


class GapFillEnricher(Enricher):
    """LAST step before compose: for the fields still MISSING in `enriched` (e.g. no
    tags/complexity) generate sensible values via LLM/web, using `original` as reference.
    ⚠️ Zero hallucinations: verifiable data or marked as generated."""

    def enrich(self, game: GameDoc) -> GameDoc:
        raise NotImplementedError("GapFillEnricher: to be implemented (LLM/web)")
