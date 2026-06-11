"""LLM call tracing: a LangChain callback handler behind a swappable factory.
One class per module, import what you need:

- `callbacks.get_trace_callbacks`: the ONLY place that knows which backend records the
  traces — attach where the LLM is built (`callbacks=get_trace_callbacks("curator")`).
- `handler.SQLiteTraceHandler`: the LangChain callback handler (default backend).
- `store.TraceStore`: the durable SQLite record of LLM calls.
- `schema.SCHEMA`: the `traces` table DDL.

Why a callback handler: LangChain fires `on_llm_start` / `on_llm_end` / `on_llm_error`
around every model call, so tracing needs ZERO changes inside the enrichers — the handler
sees the prompt, response, timing and token counts of every call, tagged per pipeline step.

Swap path (provider-agnostic, like the rest of the project): moving to Langfuse (or
LangSmith) is one new branch in `callbacks.get_trace_callbacks`:

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
