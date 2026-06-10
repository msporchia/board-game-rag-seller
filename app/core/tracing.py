"""LLM call tracing: a LangChain callback handler behind a swappable factory.

Why a callback handler: LangChain fires `on_llm_start` / `on_llm_end` / `on_llm_error`
around every model call, so tracing needs ZERO changes inside the enrichers — the handler is
attached where the LLM is built (`callbacks=get_trace_callbacks("curator")`) and sees the
prompt, response, timing and token counts of every call, tagged per pipeline step.

Swap path (provider-agnostic, like the rest of the project): `get_trace_callbacks()` is the
ONLY place that knows which backend records the traces. Moving to Langfuse (or LangSmith) is
one new branch:

    if backend == "langfuse":
        from langfuse.callback import CallbackHandler
        return [CallbackHandler()]      # reads LANGFUSE_* env vars

Nothing else in the codebase changes. The default backend is local SQLite — a `traces` table
in the same `data/seller.db` as the EnrichmentStore (zero infra, inspectable with the
sqlite3 CLI); `TRACE_BACKEND=off` disables tracing entirely.

Token counts: langchain-ollama populates `AIMessage.usage_metadata` with
`{input_tokens, output_tokens, total_tokens}` (derived from Ollama's raw `prompt_eval_count`
/ `eval_count`, which also remain available in `generation_info`/`response_metadata`).
"""

import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT,
    component      TEXT,
    model          TEXT,
    prompt_chars   INTEGER,
    prompt_preview TEXT,
    response_chars INTEGER,
    input_tokens   INTEGER,
    output_tokens  INTEGER,
    duration_ms    REAL,
    error          TEXT,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_traces_component ON traces(component);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TraceStore:
    """Durable record of LLM calls. Sibling of `EnrichmentStore` (same SQLite/WAL pattern,
    same DB file by default) but a separate class: observability must not leak into the
    system-of-record's concerns, and either can be swapped independently."""

    def __init__(self, path: str | None = None):
        self.path = path or settings.enrichment_db_path
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def save_trace(self, run_id: str, component: str, model: Optional[str],
                   prompt_chars: int, prompt_preview: str,
                   response_chars: Optional[int] = None,
                   input_tokens: Optional[int] = None, output_tokens: Optional[int] = None,
                   duration_ms: Optional[float] = None, error: Optional[str] = None) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO traces
                   (run_id, component, model, prompt_chars, prompt_preview, response_chars,
                    input_tokens, output_tokens, duration_ms, error, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, component, model, prompt_chars, prompt_preview, response_chars,
                 input_tokens, output_tokens, duration_ms, error, _now()),
            )
            self._conn.commit()

    def get_traces(self, component: str | None = None) -> list[dict]:
        if component:
            rows = self._conn.execute(
                "SELECT * FROM traces WHERE component=? ORDER BY id", (component,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM traces ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()


class SQLiteTraceHandler(BaseCallbackHandler):
    """Records every LLM call into the `traces` table.

    Cheap and fail-safe: the store opens lazily on the first write, and every write is
    wrapped in try/except — a tracing failure logs a warning and NEVER breaks the model
    call. Chat models (ChatOllama) arrive here through LangChain's documented
    `on_chat_model_start` → `on_llm_start` fallback (messages stringified), so the one
    hook covers both LLM and chat-model runs.
    """

    PREVIEW_CHARS = 200

    def __init__(self, component: str = "llm", store: TraceStore | None = None,
                 path: str | None = None):
        self.component = component
        self._path = path
        self._store = store
        self._runs: dict[UUID, dict] = {}     # run_id → start-time/prompt/model

    def _get_store(self) -> TraceStore:
        if self._store is None:
            self._store = TraceStore(path=self._path)
        return self._store

    # ---- LangChain hooks --------------------------------------------------------

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], *,
                     run_id: UUID, **kwargs: Any) -> None:
        try:
            params = kwargs.get("invocation_params") or {}
            prompt = "\n\n".join(prompts)
            self._runs[run_id] = {
                "started": time.perf_counter(),
                "model": params.get("model") or params.get("model_name"),
                "prompt_chars": len(prompt),
                "prompt_preview": prompt[: self.PREVIEW_CHARS],
            }
        except Exception:  # noqa: BLE001  tracing must never break the call path
            logger.warning("trace_start_failed", component=self.component, exc_info=True)

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        self._finish(run_id, response=response)

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self._finish(run_id, error=repr(error))

    # ---- recording --------------------------------------------------------------

    def _finish(self, run_id: UUID, response: LLMResult | None = None,
                error: str | None = None) -> None:
        run = self._runs.pop(run_id, None)
        if run is None:
            return  # end without a matched start: nothing to attribute
        try:
            duration_ms = (time.perf_counter() - run["started"]) * 1000.0
            response_chars = input_tokens = output_tokens = None
            if response is not None and response.generations:
                gen = response.generations[0][0]
                response_chars = len(gen.text or "")
                # langchain-ollama: AIMessage.usage_metadata {input,output,total}_tokens;
                # fallback to Ollama's raw counters in generation_info.
                usage = getattr(getattr(gen, "message", None), "usage_metadata", None)
                if usage:
                    input_tokens = usage.get("input_tokens")
                    output_tokens = usage.get("output_tokens")
                elif gen.generation_info:
                    input_tokens = gen.generation_info.get("prompt_eval_count")
                    output_tokens = gen.generation_info.get("eval_count")
            self._get_store().save_trace(
                run_id=str(run_id), component=self.component, model=run["model"],
                prompt_chars=run["prompt_chars"], prompt_preview=run["prompt_preview"],
                response_chars=response_chars, input_tokens=input_tokens,
                output_tokens=output_tokens, duration_ms=duration_ms, error=error,
            )
        except Exception:  # noqa: BLE001  tracing must never break the call path
            logger.warning("trace_write_failed", component=self.component, exc_info=True)


def get_trace_callbacks(component: str) -> list[BaseCallbackHandler]:
    """Callbacks to attach where an LLM is built, tagged with the pipeline step name.

    `TRACE_BACKEND` selects the backend: `sqlite` (default, local `traces` table) | `off`.
    Adding Langfuse/LangSmith is ONE new branch here — see the module docstring.
    """
    backend = settings.trace_backend.lower()
    if backend == "off":
        return []
    if backend == "sqlite":
        return [SQLiteTraceHandler(component=component)]
    logger.warning("unknown_trace_backend", backend=settings.trace_backend, fallback="disabled")
    return []
