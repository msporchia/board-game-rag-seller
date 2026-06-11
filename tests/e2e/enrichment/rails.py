"""Rails — the guardrails that keep the e2e scraping deterministic, and DERAIL loudly if it
tries to escape (see `out_of_rails.OutOfRailsError`).

The whole e2e runs the real pipeline (LLM + embeddings + DBs); the only frozen thing is the web
(search + fetch), because it is the input we don't control and the one that drifts over time.
`Rails` pins the web to recorded fixtures: two web egress points, two guards, both INJECTED
into the WebEnricher (no monkeypatching) — `railed_search.RailedSearch` raises on a query that
wasn't recorded, `railed_fetcher.RailedFetcher` raises on any page not pre-loaded into the
cache. `Rails` groups both + the page-cache seeding, so the harness doesn't have to wire the
pieces by hand.
"""

from app.core.enrichment_store import EnrichmentStore
from app.core.web_search.result import SearchResult
from tests.e2e.enrichment.railed_fetcher import RailedFetcher
from tests.e2e.enrichment.railed_search import RailedSearch


class Rails:
    """The frozen web for a set of GameCases: query-routed provider + derailing fetcher +
    page-cache seed. Inject `search` and `fetcher` into the WebEnricher and the network is
    sealed structurally — no patching involved."""

    def __init__(self, cases):
        by_query: dict[str, list[SearchResult]] = {}
        pages: dict[str, str] = {}
        for c in cases:
            by_query[c.query] = [SearchResult(**r) for r in c.search_results]
            pages.update(c.pages)
        self._search = RailedSearch(by_query)
        self._fetcher = RailedFetcher()
        self._pages = pages

    @property
    def search(self) -> RailedSearch:
        """The provider to inject into the WebEnricher."""
        return self._search

    @property
    def fetcher(self) -> RailedFetcher:
        """The fetcher to inject into the WebEnricher: any cache miss derails."""
        return self._fetcher

    @property
    def served(self) -> list[str]:
        """The web queries actually served so far."""
        return list(self._search.served)

    def seed(self, store: EnrichmentStore) -> None:
        """Pre-load the frozen pages into the page cache, so no real fetch happens."""
        for url, text in self._pages.items():
            store.save_page(url, 200, text)
