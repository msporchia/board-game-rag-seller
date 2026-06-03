"""Health-check endpoint."""

from fastapi import APIRouter

from app.config import settings
from app.core.vector_store import GameVectorStore

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "embedding_model": settings.embedding_model,
        "llm_model": settings.llm_model,
        "collection": settings.collection_name,
        "indexed_games": GameVectorStore().count(),
    }
