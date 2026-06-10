"""Seller API — FastAPI entrypoint.

Thin: builds the app and wires the routers. The logic lives in api/, ingestion/, rag/, core/.
"""

from fastapi import FastAPI

from app.api import chat, health, search
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="Seller", description="Board-game advisor bot (RAG)")

app.include_router(health.router)
app.include_router(search.router)
app.include_router(chat.router)
