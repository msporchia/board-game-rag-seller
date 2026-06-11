import hashlib

from langchain_core.embeddings import Embeddings


class FakeEmbeddings(Embeddings):
    """Deterministic, offline embeddings for the vector-store unit tests: a text maps to a
    fixed small vector via its SHA-256. No Ollama. Used to populate an in-memory Qdrant so the
    STRUCTURED filters can be tested for real — the semantic ranking is not what we assert here
    (the filters either keep or drop a point), so any stable mapping is fine."""

    def __init__(self, dim: int = 8):
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        return [h[i % len(h)] / 255.0 for i in range(self.dim)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)
