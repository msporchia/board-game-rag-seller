"""Semantic search endpoint (Phase 2): GET /search?q=...&k=5."""

from fastapi import APIRouter, Query

from app.models import GameHit
from app.rag.retriever import GameRetriever

router = APIRouter()
_retriever = GameRetriever()


@router.get("/search", response_model=list[GameHit])
def search(q: str = Query(..., description="free text, e.g. 'cooperative fantasy for two'"),
           k: int = Query(5, ge=1, le=20)):
    return _retriever.search(q, k=k)
