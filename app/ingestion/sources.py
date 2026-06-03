"""Data sources: produce GameDoc from an external source.

`GameSource` is the abstract base: to add a new source (e.g. BGG, other catalogs) you only
need a subclass that implements `fetch()` and maps to the canonical GameDoc model.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path

import httpx

from app.config import settings
from app.models import GameDoc


class GameSource(ABC):
    @abstractmethod
    def fetch(self, **kwargs) -> list[GameDoc]:
        """Return the source's games as GameDoc."""
        raise NotImplementedError


class PrestashopSource(GameSource):
    """Reads the enriched products from the PrestaShop `controller=seller` endpoint.

    The shop's canonical domain is "localhost": we connect to the container but send the
    Host header, otherwise PrestaShop responds with a 301.
    """

    def __init__(self, base_url: str | None = None, token: str | None = None,
                 host_header: str | None = None, page_size: int | None = None):
        self.base_url = base_url or settings.prestashop_base_url
        self.token = token or settings.seller_token
        self.host_header = host_header or settings.prestashop_host_header
        self.page_size = page_size or settings.seller_page_size

    def fetch(self, last_update_from: str | None = None, ids: str | None = None,
              max_pages: int | None = None) -> list[GameDoc]:
        url = f"{self.base_url}/index.php"
        games: list[GameDoc] = []
        page = 1
        with httpx.Client(timeout=120, headers={"Host": self.host_header}) as client:
            while True:
                resp = client.get(url, params=self._params(page, last_update_from, ids))
                resp.raise_for_status()
                data = resp.json()
                games.extend(GameDoc.from_dto(item) for item in data.get("products", []))
                if not data.get("hasNext") or (max_pages and page >= max_pages):
                    break
                page += 1
        return games

    def _params(self, page: int, last_update_from: str | None, ids: str | None) -> dict:
        params = {
            "fc": "module",
            "module": "utils",
            "controller": "seller",
            "token": self.token,
            "page": page,
            "pageSize": self.page_size,
        }
        if last_update_from:
            params["lastUpdateFrom"] = last_update_from
        if ids:
            params["ids"] = ids
        return params


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
