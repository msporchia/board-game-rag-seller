"""ExtractEnricher: extracts structured facts from the text into the fields (TODO)."""

from app.ingestion.enricher.enricher import Enricher
from app.models.game_doc import GameDoc


class ExtractEnricher(Enricher):
    """GUARD: mechanics/facts in the text but not in the fields? → extract them into the
    `enriched` fields (needed by the FILTERS). Requires NLP/LLM."""

    def enrich(self, game: GameDoc) -> GameDoc:
        raise NotImplementedError("ExtractEnricher: to be implemented (LLM/NLP)")
