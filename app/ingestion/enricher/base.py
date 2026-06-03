"""Enrichment pipeline base: Enricher (ABC) + EnrichmentPipeline.

Each Enricher is a STRATEGY with a GUARD (acts only when needed); the pipeline applies them
in order (Chain of Responsibility). They work on the `game.enriched` working copy, leaving
`game.original` (hard-truth) untouched.
"""

from abc import ABC, abstractmethod

from app.models import GameDoc


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
            game = step.enrich(game)
        return game


def with_enriched(game: GameDoc, **updates) -> GameDoc:
    """Helper: new GameDoc with an updated `enriched` (original untouched)."""
    return game.model_copy(update={"enriched": game.enriched.model_copy(update=updates)})
