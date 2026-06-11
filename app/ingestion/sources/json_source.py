import json
from pathlib import Path

from app.ingestion.sources.source import GameSource
from app.models.game_doc import GameDoc


class JsonSource(GameSource):
    """Source from a list of GameDoc dicts (or from a JSON file).

    Used by the test harness to feed the system "exactly the API DTO" in a reproducible,
    offline way. Doubles as an interim 'JSON export'.
    """

    def __init__(self, games: list[dict] | None = None, path: str | None = None):
        if games is None and path is not None:
            games = json.loads(Path(path).read_text(encoding="utf-8"))
        self._games = games or []

    def fetch(self, **kwargs) -> list[GameDoc]:
        return [GameDoc.from_dto(g) for g in self._games]
