"""Centralized access to the vector store.

A single place where embeddings (Ollama) and the Qdrant client live: ingest, retriever and
recommender use this class instead of each re-creating its own connection.
`collection_name` is overridable (e.g. 'games_test' for the evaluation harness).
"""

import uuid

from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models as qm

from app.config import settings


class GameVectorStore:
    def __init__(self, config=settings, collection_name: str | None = None,
                 client: QdrantClient | None = None, embeddings=None):
        self.config = config
        self.collection_name = collection_name or config.collection_name
        self.embeddings = embeddings or OllamaEmbeddings(
            model=config.embedding_model, base_url=config.ollama_url
        )
        # An injected client (e.g. QdrantClient(location=":memory:") for the unit tests) takes a
        # different, client-based index path — `from_documents(url=...)` would ignore it.
        self._external_client = client is not None
        self.client = client or QdrantClient(url=config.qdrant_url)

    @staticmethod
    def point_id(id_product: int) -> str:
        """Stable, deterministic ID for the Qdrant point (so the re-ingest upserts instead
        of duplicating). UUID v5 derived from the product id."""
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"seller-game:{id_product}"))

    def _store(self) -> QdrantVectorStore:
        return QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
        )

    def index(self, documents: list[Document], ids: list[str] | None = None, recreate: bool = True) -> None:
        if self._external_client:
            self._index_with_client(documents, ids=ids, recreate=recreate)
        elif recreate:
            QdrantVectorStore.from_documents(
                documents,
                embedding=self.embeddings,
                url=self.config.qdrant_url,
                collection_name=self.collection_name,
                ids=ids,
                force_recreate=True,
            )
        else:
            self._store().add_documents(documents, ids=ids)

    def _index_with_client(self, documents: list[Document], ids: list[str] | None, recreate: bool) -> None:
        """Index through the injected client (in-memory tests): `from_documents(url=...)` builds
        its own client, so we create the collection on our client and add through it."""
        coll = self.collection_name
        if recreate and self.client.collection_exists(coll):
            self.client.delete_collection(coll)
        if not self.client.collection_exists(coll):
            dim = len(self.embeddings.embed_query("probe"))
            self.client.create_collection(
                coll, vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE)
            )
        self._store().add_documents(documents, ids=ids)

    def search(self, query: str, k: int = 5, query_filter=None):
        """Similarity search: returns [(Document, score), ...]."""
        return self._store().similarity_search_with_score(query, k=k, filter=query_filter)

    def count(self) -> int:
        try:
            return self.client.count(self.collection_name, exact=True).count
        except Exception:
            return 0
