"""Fakes local to the SearchCatalogTool unit — a retriever that records its calls, offline."""

from app.models.game_hit import GameHit


def make_hit(id_product: int, name: str, **overrides) -> GameHit:
    data = {"score": 0.9, "id_product": id_product, "name": name}
    data.update(overrides)
    return GameHit(**data)


class FakeRetriever:
    """Returns a preset list of hits (cut to k); records every (query, k, filters) call."""

    def __init__(self, hits: list[GameHit]):
        self.hits = hits
        self.calls: list[tuple] = []

    def search(self, query: str, k: int = 5, filters=None) -> list[GameHit]:
        self.calls.append((query, k, filters))
        return self.hits[:k]
