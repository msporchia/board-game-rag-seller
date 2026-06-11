from app.core.web_search.provider import WebSearchProvider
from app.core.web_search.result import SearchResult
from tests.e2e.enrichment.out_of_rails import OutOfRailsError


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
