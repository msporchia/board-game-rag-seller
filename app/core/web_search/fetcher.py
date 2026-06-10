import logging

import httpx
import trafilatura

from app.config import settings

logger = logging.getLogger(__name__)


class PageFetcher:
    """Downloads a page with a browser UA and returns the clean main text (no nav/boilerplate).
    Empty string on error or non-extractable page. Injectable into the WebEnricher (like the
    search provider), so tests swap it instead of monkeypatching a module-level function."""

    def __init__(self, max_chars: int | None = None):
        self.max_chars = max_chars or settings.web_fetch_chars

    def fetch(self, url: str) -> str:
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
        return text[: self.max_chars].strip()
