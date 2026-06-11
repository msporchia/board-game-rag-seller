from langchain_core.callbacks import BaseCallbackHandler

from app.config import settings
from app.core.logging import get_logger
from app.core.tracing.handler import SQLiteTraceHandler

logger = get_logger(__name__)


def get_trace_callbacks(component: str) -> list[BaseCallbackHandler]:
    """Callbacks to attach where an LLM is built, tagged with the pipeline step name.

    `TRACE_BACKEND` selects the backend: `sqlite` (default, local `traces` table) | `off`.
    Adding Langfuse/LangSmith is ONE new branch here — see the package docstring.
    """
    backend = settings.trace_backend.lower()
    if backend == "off":
        return []
    if backend == "sqlite":
        return [SQLiteTraceHandler(component=component)]
    logger.warning("unknown_trace_backend", backend=settings.trace_backend, fallback="disabled")
    return []
