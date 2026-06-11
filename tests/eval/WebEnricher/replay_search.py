from app.core.web_search.provider import WebSearchProvider
from app.core.web_search.result import SearchResult


class ReplaySearch(WebSearchProvider):
    """Returns RECORDED search results (zero network)."""

    def __init__(self, results: list[dict]):
        self._results = [SearchResult(**r) for r in results]

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        return self._results[:max_results]
