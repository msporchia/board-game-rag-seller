"""Enrichment pipeline base: Enricher (ABC) + EnrichmentPipeline.

Each Enricher is a STRATEGY with a GUARD (acts only when needed); the pipeline applies them
in order (Chain of Responsibility). They work on the `game.enriched` working copy, leaving
`game.original` (hard-truth) untouched.
"""

import logging
import time
from abc import ABC, abstractmethod

from app.models import GameDoc

logger = logging.getLogger(__name__)


class Enricher(ABC):
    @abstractmethod
    def enrich(self, game: GameDoc) -> GameDoc:
        """Return the (possibly) modified GameDoc. Idempotent when no action is needed."""
        raise NotImplementedError


class EnrichmentPipeline:
    """Applies an ordered sequence of Enrichers. The order is part of the strategy."""

    def __init__(self, steps: list[Enricher] | None = None):
        self.steps = steps or []

    def run(self, game: GameDoc) -> GameDoc:
        for step in self.steps:
            t0 = time.perf_counter()
            game = step.enrich(game)
            logger.info("step=%s game=%s done in %.2fs",
                        type(step).__name__, game.id_product, time.perf_counter() - t0)
        return game


def with_enriched(game: GameDoc, **updates) -> GameDoc:
    """Helper: new GameDoc with an updated `enriched` (original untouched)."""
    return game.model_copy(update={"enriched": game.enriched.model_copy(update=updates)})
