import httpx

from app.config import settings
from app.ingestion.sources.source import GameSource
from app.models.game_doc import GameDoc


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
