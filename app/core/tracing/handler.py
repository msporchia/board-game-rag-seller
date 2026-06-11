import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.core.logging import get_logger
from app.core.tracing.store import TraceStore

logger = get_logger(__name__)


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
