from abc import ABC, abstractmethod

from app.core.web_search.result import SearchResult


class WebSearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int) -> list[SearchResult]:
        raise NotImplementedError
