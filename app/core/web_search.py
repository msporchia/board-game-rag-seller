"""Web search + fetch for the WebEnricher.

Two responsibilities, behind swappable abstractions (like embeddings/LLM):
  - `WebSearchProvider`: "throw a query at an engine, get back a list of URLs" (discovery).
    Default `DdgsSearch` (free, no API key); in prod you swap in Tavily/Brave.
  - `fetch_clean()`: downloads a page with a browser User-Agent (many sources block "bare"
    fetchers: 403/401) and extracts the clean text (trafilatura).

NO LLM here: just network I/O. The logic (whitelist, judgment, extraction) lives in the
WebEnricher.
"""

import logging
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import httpx
import trafilatura
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    title: str = ""
    url: str
    snippet: str = ""

    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc.lower().removeprefix("www.")


class WebSearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int) -> list[SearchResult]:
        raise NotImplementedError


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


def fetch_clean(url: str, max_chars: int | None = None) -> str:
    """Download `url` with a browser UA and return the clean main text (no nav/boilerplate).
    Empty string on error or non-extractable page."""
    max_chars = max_chars or settings.web_fetch_chars
    try:
        resp = httpx.get(
            url,
            headers={
                "User-Agent": settings.web_user_agent,
                "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
            },
            timeout=20,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except Exception:  # noqa: BLE001  network/4xx/5xx → page skipped
        logger.warning("fetch failed (url=%s)", url, exc_info=True)
        return ""
    text = trafilatura.extract(resp.text) or ""
    return text[:max_chars].strip()
