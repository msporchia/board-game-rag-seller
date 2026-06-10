"""Structured logging — structlog events rendered through stdlib `logging`.

Modules log EVENTS with FIELDS instead of values interpolated into prose:

    logger = get_logger(__name__)
    logger.info("search_done", query=q, k=5, hits=3, duration_ms=142)

so a value is a field (greppable in dev, indexable by a log platform), never a
substring to regex out of a sentence. `LOG_FORMAT` picks the renderer:
`console` (default: human-readable key=value lines) or `json` (one object per
line, ready for Loki/Datadog/whatever reads stdout — the app never knows).

One pipeline for everything: structlog routes into stdlib logging, and the
single root handler renders BOTH structlog events and foreign records (uvicorn,
libraries) through the same processor chain. Context bound via
`structlog.contextvars` (e.g. `game=<id>` for the whole enrichment of a game,
see the ingester) is merged into every event emitted underneath it.

Each entrypoint (FastAPI app, `python -m app.ingestion.ingester`) calls
`setup_logging()` once; the level comes from `LOG_LEVEL` (settings, default INFO).
"""

import logging
import sys

import structlog

from app.config import settings

_configured = False

# Shared by both paths: structlog-native events and foreign stdlib records.
_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]

# Module-import time, deliberately: modules call `get_logger` before any entrypoint
# runs, and events must route into stdlib logging even when `setup_logging()` was
# never called (tests with caplog, embedding apps with their own handlers).
structlog.configure(
    processors=_PROCESSORS + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Project-wide logger factory: a structlog BoundLogger backed by stdlib."""
    return structlog.get_logger(name)


def _renderer():
    if settings.log_format.lower() == "json":
        return structlog.processors.JSONRenderer()
    return structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())


def _formatter() -> logging.Formatter:
    """The one formatter: renders structlog events and foreign records alike."""
    return structlog.stdlib.ProcessorFormatter(
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    _renderer()],
        foreign_pre_chain=_PROCESSORS,
    )


def setup_logging(level: str | None = None) -> None:
    """Configure the root logger. Idempotent: repeated calls (e.g. uvicorn reload, tests)
    do not stack handlers or override the first configuration."""
    global _configured
    if _configured:
        return
    root = logging.getLogger()
    if not root.handlers:  # respect an embedding app's handlers (e.g. pytest, uvicorn)
        handler = logging.StreamHandler()
        handler.setFormatter(_formatter())
        root.addHandler(handler)
    root.setLevel((level or settings.log_level).upper())
    _configured = True
