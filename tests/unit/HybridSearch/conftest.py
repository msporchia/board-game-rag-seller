"""Fixtures LOCAL to the HybridSearch unit: a real Qdrant in **in-memory** mode
(`QdrantClient(location=":memory:")`) + deterministic `FakeEmbeddings` — no server, no Ollama.

Same isolation principle as the EnrichmentStore unit (`EnrichmentStore(path=":memory:")`): the
store lives in-process and dies with the test, so we never touch the real DB. We index a small,
hand-built corpus whose payloads are known exactly, then assert which games the STRUCTURED
filters keep or drop. The in-memory Qdrant runs the *same* filter semantics as production, so the
test is faithful (not a mock of the filter logic)."""

import pytest
from langchain_core.documents import Document
from qdrant_client import QdrantClient

from app.core.vector_store import GameVectorStore
from app.rag.retriever import GameRetriever
from tests.factories.embeddings import FakeEmbeddings

# Known corpus: each game's payload is fixed so the expected filter results are unambiguous.
# Note D has duration_min/complexity_level = None (missing data) and E is an expansion.
# cooperative: Bravo & Delta are co-op (True), Alpha is explicitly competitive (False), the rest
# leave the field absent (UNKNOWN) — so a hard `cooperative: True` keeps only {2, 4}.
GAMES = [
    {"id_product": 1, "name": "Alpha", "players": [2], "duration_min": 30, "complexity_level": 2,
     "age_min": 8, "year": 2018, "internal_rating": 7.5, "is_expansion": False, "categoria": "carte",
     "cooperative": False},
    {"id_product": 2, "name": "Bravo", "players": [2, 3, 4], "duration_min": 60, "complexity_level": 3,
     "age_min": 10, "year": 2020, "internal_rating": 8.0, "is_expansion": False, "categoria": "tavolo",
     "cooperative": True},
    {"id_product": 3, "name": "Charlie", "players": [3, 4, 5], "duration_min": 120, "complexity_level": 4,
     "age_min": 12, "year": 2015, "internal_rating": 6.0, "is_expansion": False, "categoria": "tavolo"},
    {"id_product": 4, "name": "Delta", "players": [1, 2], "duration_min": None, "complexity_level": None,
     "age_min": 14, "year": 2022, "internal_rating": 7.0, "is_expansion": False, "categoria": "tavolo",
     "cooperative": True},
    {"id_product": 5, "name": "Echo", "players": [4], "duration_min": 45, "complexity_level": 1,
     "age_min": 6, "year": 2019, "internal_rating": 5.5, "is_expansion": True, "categoria": "carte"},
    {"id_product": 6, "name": "Foxtrot", "players": [2, 3], "duration_min": 90, "complexity_level": 5,
     "age_min": 14, "year": 2012, "internal_rating": 8.5, "is_expansion": False, "categoria": "carte"},
]


@pytest.fixture
def store():
    s = GameVectorStore(
        client=QdrantClient(location=":memory:"),
        embeddings=FakeEmbeddings(),
        collection_name="games_test",
    )
    docs = [Document(page_content=g["name"], metadata=g) for g in GAMES]
    ids = [GameVectorStore.point_id(g["id_product"]) for g in GAMES]
    s.index(docs, ids=ids, recreate=True)
    return s


@pytest.fixture
def retriever(store):
    return GameRetriever(store=store)
