from abc import ABC, abstractmethod

from app.models.game_doc import GameDoc


class GameSource(ABC):
    @abstractmethod
    def fetch(self, **kwargs) -> list[GameDoc]:
        """Return the source's games as GameDoc."""
        raise NotImplementedError
