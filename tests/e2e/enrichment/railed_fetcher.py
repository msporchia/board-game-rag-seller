from app.core.web_search.fetcher import PageFetcher
from tests.e2e.enrichment.out_of_rails import OutOfRailsError


class RailedFetcher(PageFetcher):
    """Drop-in fetcher that NEVER touches the network. Every expected page is pre-loaded into
    the page cache → WebEnricher._fetch serves it from there and never reaches here. A call to
    `fetch` means a cache miss (an URL the fixtures don't cover) → we derail instead of going
    online."""

    def __init__(self):
        pass  # no settings needed: this fetcher only raises

    def fetch(self, url: str) -> str:
        raise OutOfRailsError(
            f"fetch left the rails: fetch({url!r}) — page not pre-recorded.\n"
            "The WebEnricher tried to download an URL the fixtures don't cover (ranking/fetch "
            "changed or stale fixtures) → re-record with `python -m tests.e2e.enrichment record`."
        )
