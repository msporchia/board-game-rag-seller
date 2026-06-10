"""Structured logging setup — stdlib `logging` only, no new dependencies.

One consistent line format across the API and the ingester CLI:

    2026-06-10 12:00:00,123 INFO    app.rag.retriever - search query='...' k=5 ...

Each entrypoint (FastAPI app, `python -m app.ingestion.ingester`) calls `setup_logging()`
once; modules just use `logging.getLogger(__name__)`. The level comes from `LOG_LEVEL`
(`settings.log_level`, default INFO) via the existing pydantic-settings config.
"""

import logging

from app.config import settings

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s - %(message)s"
_configured = False


def setup_logging(level: str | None = None) -> None:
    """Configure the root logger. Idempotent: repeated calls (e.g. uvicorn reload, tests)
    do not stack handlers or override the first configuration."""
    global _configured
    if _configured:
        return
    root = logging.getLogger()
    if not root.handlers:  # respect an embedding app's handlers (e.g. pytest, uvicorn)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(handler)
    root.setLevel((level or settings.log_level).upper())
    _configured = True
