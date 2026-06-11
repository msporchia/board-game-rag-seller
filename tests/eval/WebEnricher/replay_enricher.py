from app.ingestion.enricher.web import WebEnricher


class ReplayWebEnricher(WebEnricher):
    """WebEnricher with `_fetch` served from RECORDED pages: the only live part is the LLM."""

    def __init__(self, pages: dict[str, str], **kwargs):
        super().__init__(**kwargs)
        self._pages = pages

    def _fetch(self, url: str) -> str:
        return self._pages.get(url, "")
