"""Seller API — FastAPI entrypoint.

Thin: builds the app and wires the routers. The logic lives in api/, ingestion/, rag/, core/.
"""

from fastapi import FastAPI

from app.api import health, search

app = FastAPI(title="Seller", description="Board-game advisor bot (RAG)")

app.include_router(health.router)
app.include_router(search.router)
