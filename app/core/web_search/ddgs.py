import logging

from app.config import settings
from app.core.web_search.provider import WebSearchProvider
from app.core.web_search.result import SearchResult

logger = logging.getLogger(__name__)


class DdgsSearch(WebSearchProvider):
    """DuckDuckGo via `ddgs`: free and no API key. Flakier than a paid search API
    (rate-limits), but enough for local-first/experimentation."""

    def __init__(self, region: str | None = None):
        self.region = region or settings.web_search_region

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        from ddgs import DDGS
        try:
            rows = DDGS().text(query, region=self.region, max_results=max_results)
        except Exception:  # noqa: BLE001  flaky engine/rate-limit → no results this round
            logger.warning("ddgs search failed (query=%r)", query, exc_info=True)
            return []
        return [
            SearchResult(
                title=r.get("title", ""), url=r.get("href", ""), snippet=r.get("body", "")
            )
            for r in rows
            if r.get("href")
        ]
