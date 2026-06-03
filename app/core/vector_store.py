"""Centralized access to the vector store.

A single place where embeddings (Ollama) and the Qdrant client live: ingest, retriever and
recommender use this class instead of each re-creating its own connection.
`collection_name` is overridable (e.g. 'games_test' for the evaluation harness).
"""

import uuid

from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from app.config import settings


class GameVectorStore:
    def __init__(self, config=settings, collection_name: str | None = None):
        self.config = config
        self.collection_name = collection_name or config.collection_name
        self.embeddings = OllamaEmbeddings(
            model=config.embedding_model, base_url=config.ollama_url
        )
        self.client = QdrantClient(url=config.qdrant_url)

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
        if recreate:
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

    def search(self, query: str, k: int = 5, query_filter=None):
        """Similarity search: returns [(Document, score), ...]."""
        return self._store().similarity_search_with_score(query, k=k, filter=query_filter)

    def count(self) -> int:
        try:
            return self.client.count(self.collection_name, exact=True).count
        except Exception:
            return 0
