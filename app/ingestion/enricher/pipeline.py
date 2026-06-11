import time

from app.core.logging import get_logger
from app.ingestion.enricher.enricher import Enricher
from app.models.game_doc import GameDoc

logger = get_logger(__name__)


class EnrichmentPipeline:
    """Applies an ordered sequence of Enrichers (Chain of Responsibility). The order is part
    of the strategy."""

    def __init__(self, steps: list[Enricher] | None = None):
        self.steps = steps or []

    def run(self, game: GameDoc) -> GameDoc:
        for step in self.steps:
            t0 = time.perf_counter()
            game = step.enrich(game)
            logger.info("enrich_step", step=type(step).__name__, game=game.id_product,
                        duration_ms=round((time.perf_counter() - t0) * 1000))
        return game
