# Eval & observability — status and roadmap

What we can measure today, what we are blind to, and the planned work. Same discipline as the
rest of the project: every item below should land with numbers and a short write-up of what it
caught, not just tooling for its own sake.

## What exists today

| Capability | Where | What it gives us |
|---|---|---|
| Retrieval scorecard | `tests/eval.py`, [`valutazione.md`](valutazione.md) | recall@K and ranks on frozen queries — rank-based, because cosine scores are uncalibrated |
| Regression gate | `tests/e2e/enrichment/` + versioned `baseline.json` | no metric may regress beyond tolerance vs the committed baseline |
| Per-step LLM evals | `tests/eval/<Unit>/` + `tests/eval.py --pipeline …` | each enrichment/chat step measured against hand-written oracles |
| Chat eval suites | `tests/eval/TurnAnalyzer`, `ChatRetrieve`, `ChatPitch`, `ChatConversation` | turn reading, retrieval, grounded pitch, and whole-session convergence measured on scripted cases |
| Invariants in code | `WebEnricher` (quote verification), `ChatAdvisor` (id grounding) | anti-hallucination enforced at runtime, not just tested |
| Structured logging | `app/core/logging.py` (structlog) + per-module loggers | every log is an EVENT with FIELDS (`enrich_step`, `game=2845`, `duration_ms=140`): step, game id, duration, outcome for every pipeline step; query/k/filters/hits/latency for every search; failed LLM/web calls log a warning instead of vanishing. `LOG_FORMAT=json` makes the same events machine-shippable |
| LLM call tracing | `app/core/tracing/` (`traces` table in `data/seller.db`) | every Curator/Web/Synth call recorded: component, model, prompt size+preview, response size, latency, token counts |

## What we are blind to

- **No client-closed loop yet.** Chat quality is now measured offline, but the storefront loop is
  not closed: no real `seller-web`/`seller-shop` transcript, no card-click/add-to-cart/purchase
  event joined back to `session_id`, and no recorded showcase trace for the UI path.
- **No LLM-judge layer for chat prose yet.** The current suites use rule scoring and scripted
  oracles; they catch convergence, filters, fallback and grounding shape, but not nuanced sales
  copy quality.
- **No runtime metrics.** Per-turn latency is known anecdotally (~50–130 s on CPU), with no
  retrieval-vs-generation breakdown. (The `traces` table now gives the generation half per
  call; the per-turn split is still unmeasured.)
- **Embeddings are not traced.** LangChain's callback system covers LLM runs only —
  `OllamaEmbeddings` exposes no callbacks. Embedding cost shows up in the indexing/search
  duration logs instead.

## Design — logging & tracing

**Structured logging** is structlog over stdlib `logging`: modules log events with fields
(`logger.info("search_done", query=q, hits=3, duration_ms=142)`), never values interpolated
into prose — a value is a field to index, not a substring to regex out of a sentence.
`setup_logging()` (idempotent, called by the API entrypoint and the ingester CLI) attaches
ONE root handler whose `ProcessorFormatter` renders both structlog events and foreign
records (uvicorn, libraries) through the same chain; `LOG_FORMAT` picks `console`
(human-readable, default) or `json` (one object per line on stdout — the twelve-factor
contract: the app never knows where logs are shipped, the platform does). During enrichment
the ingester binds `game=<id>` via `structlog.contextvars`, so every event emitted by any
module while that game is in the pipeline carries the game id. The previously silent
`except Exception` paths (curator/web/synth LLM calls, ddgs search, page fetch, Qdrant
count) log warnings without changing control flow.

**Why a callback handler for tracing.** LangChain fires `on_llm_start` / `on_llm_end` /
`on_llm_error` around every model call, so tracing needs zero changes inside the enrichers:
each ChatOllama construction site attaches `callbacks=get_trace_callbacks("<component>")`
and the handler sees prompt, response, timing and token counts, attributed per pipeline step.
The handler is fail-safe by design — its writes are wrapped, a tracing failure logs a
warning and never breaks the model call.

**The swap path** (the same provider-agnostic discipline as embeddings/LLM/search):
`get_trace_callbacks()` in `app/core/tracing/callbacks.py` is the only place that knows which backend
records traces. `TRACE_BACKEND=sqlite` (default) returns the local `SQLiteTraceHandler`;
`off` disables tracing; moving to Langfuse (self-hosted, fits the no-cloud-keys constraint)
or LangSmith is **one new branch** returning that provider's handler — nothing else changes.

**What a trace row contains** (`traces` table, same SQLite/WAL file as the enrichment
store, separate `TraceStore` class): `run_id`, `component` (curator/web/synth), `model`,
`prompt_chars` + `prompt_preview` (first 200 chars), `response_chars`, `input_tokens` /
`output_tokens` (from langchain-ollama's `usage_metadata`, i.e. Ollama's `prompt_eval_count`
/ `eval_count`), `duration_ms`, `error`, `created_at`.

Inspecting traces, e.g. slowest calls per component:

```sql
SELECT component, COUNT(*) AS calls,
       ROUND(AVG(duration_ms)) AS avg_ms, ROUND(MAX(duration_ms)) AS worst_ms,
       SUM(output_tokens) AS out_tokens
FROM traces GROUP BY component ORDER BY avg_ms DESC;
```

## Roadmap (TODO)

- [x] **Structured logging** across pipeline and API: step, game id, duration, outcome.
      (`app/core/logging.py` — see Design below.)
- [x] **LLM call tracing**: every Curator/Web/Synth call traced with prompt, latency,
      tokens, behind a swappable factory (`app/core/tracing/`); local SQLite backend now,
      Langfuse/LangSmith = one new factory branch. Chat-advisor calls still to be wired
      (the chat module is being reworked).
- [ ] **Trace dashboard** — when canned SQL stops being enough: Arize Phoenix as a
      `TRACE_BACKEND=phoenix` factory branch (open source, single local process, no extra
      infra — unlike Langfuse v3's Postgres+ClickHouse stack). The trace row already maps
      onto the OpenTelemetry GenAI semantic conventions (`gen_ai.request.model`,
      `gen_ai.usage.input_tokens`/`output_tokens`), so any OTel-native backend can consume
      the same data.
- [x] **Chat-level eval baseline**: TurnAnalyzer, ChatRetrieve, ChatPitch and ChatConversation
      produce persisted reports with per-case failures and cost/usage where relevant.
- [ ] **Chat showcase / client loop**: record one real session through the API and frontends,
      including rendered cards, quick-reply clicks, trace, and the response contract used by
      `seller-web` / `seller-shop`.
- [ ] **Chat LLM-judge layer**: sales-copy quality and subtle groundedness scored automatically
      (LLM-as-judge, with the same record/replay discipline as the web rails).
- [ ] **Latency budget**: measure the retrieval vs generation split per `/chat` turn; document
      CPU vs GPU numbers.
- [ ] **RAGAS** (or similar) alongside the in-house scorecard — to compare methodologies; the
      scorecard remains the gate.
- [x] **CI split**: the unit suite (235 tests, offline, ~2-3 s locally) runs on GitHub Actions; evals
      and e2e stay local by design — they need a running Ollama and ~5 GB of models, which is
      neither free nor fast on hosted runners. The split is deliberate and documented, not a
      hidden limitation.
