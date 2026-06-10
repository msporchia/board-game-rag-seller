from urllib.parse import urlparse

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str = ""
    url: str
    snippet: str = ""

    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc.lower().removeprefix("www.")
