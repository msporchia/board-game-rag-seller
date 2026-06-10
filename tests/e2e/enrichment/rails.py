"""Rails — the guardrails that keep the e2e scraping deterministic, and DERAIL loudly if it
tries to escape.

The whole e2e runs the real pipeline (LLM + embeddings + DBs); the only frozen thing is the web
(search + fetch), because it is the input we don't control and the one that drifts over time.
`Rails` pins the web to recorded fixtures and — the key point — turns any unexpected network
attempt into an `OutOfRailsError` instead of degrading silently (today `DdgsSearch.search` /
`PageFetcher.fetch` swallow exceptions and return []/"" → a game would come back un-enriched and
the test would still pass on a degraded result: exactly the silent failure we want to catch).

Two web egress points, two guards, both INJECTED into the WebEnricher (no monkeypatching):
  - the search provider (`RailedSearch`) raises on a query that wasn't recorded;
  - the fetcher (`RailedFetcher`) raises on any page not pre-loaded into the cache.

`Rails` groups both + the page-cache seeding, so the harness doesn't have to wire the pieces
by hand.
"""

from app.core.enrichment_store import EnrichmentStore
from app.core.web_search.fetcher import PageFetcher
from app.core.web_search.provider import WebSearchProvider
from app.core.web_search.result import SearchResult


class OutOfRailsError(RuntimeError):
    """The frozen scraping tried something the fixtures don't cover. Almost always: the
    webscraper (query/ranking/fetch) changed and the e2e fixtures are stale → re-record with
    `python -m tests.e2e.enrichment record`."""


class RailedSearch(WebSearchProvider):
    """Provider served from RECORDED results, routed by exact query. Unlike the eval's
    ReplaySearch (which ignores the query), this routes by query so one instance can serve several
    games in one ingest — and raises on an unknown query, derailing if `_query` changes."""

    def __init__(self, by_query: dict[str, list[SearchResult]]):
        self._by_query = by_query
        self.served: list[str] = []   # queries actually requested (proof the Web step ran)

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        self.served.append(query)
        if query not in self._by_query:
            raise OutOfRailsError(
                f"search left the rails: query {query!r} was not recorded.\n"
                f"Known queries: {sorted(self._by_query)}.\n"
                "Likely cause: WebEnricher._query changed or the corpus name changed → "
                "re-record with `python -m tests.e2e.enrichment record`."
            )
        return self._by_query[query][:max_results]


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
