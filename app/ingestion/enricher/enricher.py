from abc import ABC, abstractmethod

from app.models.game_doc import GameDoc


class Enricher(ABC):
    """A STRATEGY with a GUARD (acts only when needed). Enrichers work on the `game.enriched`
    working copy, leaving `game.original` (hard-truth) untouched."""

    @abstractmethod
    def enrich(self, game: GameDoc) -> GameDoc:
        """Return the (possibly) modified GameDoc. Idempotent when no action is needed."""
        raise NotImplementedError
