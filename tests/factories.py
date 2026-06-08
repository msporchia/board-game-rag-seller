"""Shared test helpers: GameDoc factory + fake LLM transport + fake embeddings.

No fixtures here (those live in conftest.py): only importable constructors usable from any
test, so `make_game`/`FakeLLM`/`FakeEmbeddings` work both in tests and in fixtures.
"""

import hashlib

from langchain_core.embeddings import Embeddings

from app.models import GameDoc


def make_game(**overrides) -> GameDoc:
    """Test GameDoc with sensible defaults; `overrides` overrides the DTO fields."""
    dto = {"id_product": 1, "name": "Test Game", "description": "Una descrizione di prova."}
    dto.update(overrides)
    return GameDoc.from_dto(dto)


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    """Fake LLM transport: `.invoke()` ignores the prompt and always returns the same
    `content`. Makes the LLM-step tests DETERMINISTIC without touching Ollama.
    Records the received prompts in `.calls` for optional asserts."""

    def __init__(self, content: str = ""):
        self.content = content
        self.calls: list[str] = []

    def invoke(self, prompt: str) -> _FakeResponse:
        self.calls.append(prompt)
        return _FakeResponse(self.content)


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
