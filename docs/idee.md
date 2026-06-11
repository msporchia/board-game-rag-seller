# Ideas — levers to evaluate when doing the next step

Operational brain-dump of things **not yet touched** or only noted elsewhere. Each entry:
*what it is · why it's worth it · how to do it concretely · what to measure to decide*. No
promise to do them: it's here to review when choosing the next piece of work.

Rough priority (perceived ROI · effort): **HIGH** = as soon as possible; **MEDIUM** = when the
context requires it; **LOW** = nice-to-have / when scaling.

---

## A. Structured output with schema enforcement — HIGH

- **What**: today `format="json"` + `json.loads()` + `try/except` (see
  `CuratorEnricher._ask_llm`, `WebEnricher._run_llm`). With a local 8B the malformed-JSON risk
  is real (the Curator's v1→v4 history attests to it).
- **Why**: every broken JSON = a lost batch → a label that ends up in missing for transport
  reasons, not content. It pollutes the metric.
- **How (3 options, from lightest to most radical)**:
  1. `ChatOllama.with_structured_output(PydanticModel)` — minimal change, stays in LangChain,
     internal retry if the Pydantic validation fails.
  2. **Instructor** (`pip install instructor`): wraps Ollama, Pydantic schema, retry +
     validation for free. Less boilerplate than the LangChain path.
  3. **Outlines**: constrains GENERATION at the sampling level (grammar/JSON schema). More
     invasive but eliminates malformed JSON *by construction*, not by retry. Worth it
     especially with small models (≤8B).
- **Measure**: the `LLM-PARSE-FAIL` rate in the `runs/` report. Before/after. Expected: → 0.

## B. Tracing/observability — HIGH

- **What**: today all the visibility into what the LLM does is the JSON persisted in `runs/`
  and the session `print`s. To debug "why did it get *this* case wrong" you go by hand.
- **Why**: the future chat (tier-routing Haiku→Sonnet, see `note.md`) is NOT debuggable
  without tracing. And even today, understanding the cause of a Curator FP costs minutes
  instead of seconds.
- **How**: **self-hosted Langfuse** (docker compose, ~1h setup). 1-line integration with
  `ChatOllama` via a callback handler. Per-call timeline: prompt, output, latency, cost (future
  cloud), tags, built-in LLM-as-judge eval.
  - Alternatives: Arize Phoenix (open source, more embedding-viz); LangSmith (paid SaaS).
- **Measure**: time to diagnose a failed eval case. Expected: minutes → seconds.

## C. Multilingual embedder — HIGH (on retrieval)

- **What**: today `nomic-embed-text` (768d, EN-centric). Already flagged in `note.md` and
  `stato.md` as weak on Italian.
- **Why**: the `rule` baseline sits at Recall@5 = 0.26 with half the queries including specific
  Italian terms (mitologia, gestionale, cooperativo). The embedder is a lever parallel to the
  enricher: you change the data with the Curator/Synth, you change the *mapping* here.
- **How**: pull `bge-m3` (BAAI, strong multilingual, 1024d) or `multilingual-e5-large` via
  Ollama / sentence-transformers. Swap it in `app/core/vector_store.py`.
- **Measure**: `docker exec seller-api python -m tests.eval --suite core --k 5` before/after.
  Expected: +5÷10 Recall@5 points over the baseline, **without** touching the rest of the
  pipeline.
- **Note**: the vector dimension changes → recreate the Qdrant collection (`recreate=True`
  already enabled in `Ingester`).

## D. LLM model — MEDIUM (once the Curator stabilizes)

- **What**: today `llama3.1` (8B). The Curator's 7 residual fails are fine errors, some
  potentially curable with the model.
- **Why**: 8B on JSON + IT is the weak point; Qwen2.5-7B/14B-instruct and Gemma 9B historically
  follow instructions better and produce cleaner structured output.
- **How**: `ollama pull qwen2.5:7b-instruct` (or `:14b` if the VRAM holds after offload),
  change `settings.llm_model`, re-run the Curator eval and diff against the previous `runs/`.
- **Measure**: F0.5 on the Curator eval. Expected: +5÷15% if the model is better at the "genre"
  classification (the dominant fail pattern).
- **Prerequisite**: also save the model **digest** (not just the name) in the evals (see section
  H). Otherwise the diff vs the previous run becomes misleading if Ollama updates the pin
  underneath.

## E. LiteLLM as transport — LOW (but a MUST when going to cloud)

- **What**: today `ChatOllama` from `langchain_ollama`. Works, but it's Ollama-specific.
- **Why**: the day you test Haiku/Sonnet/Gemini for the chat (or even just for the Synth) you
  don't want to rewrite the transport.
- **How**: `litellm` exposes a UNIFORM OpenAI-compatible API over Ollama / vLLM / Anthropic /
  OpenAI / Gemini. Change one config string: `model="ollama/llama3.1"` →
  `model="anthropic/claude-haiku-4-5"`.
- **Measure**: none today; when you want to compare local vs cloud on a task (e.g. Synth), zero
  refactor.

## F. SynthEnricher eval (when it gets written) — MEDIUM

- **What**: slot-filling F-β is right for the Curator (extraction), NOT for the synthesis
  (Synth = generating a paragraph).
- **Why**: a synthesis must be measured on *faithfulness* (doesn't invent), *completeness*
  (covers the facts), *relevance* (stays on the game). Those are guided LLM-as-judge.
- **How**: **Ragas** (`pip install ragas`) — canonical RAG metrics (`faithfulness`,
  `answer_relevancy`, `context_precision`), runs a controlled LLM-as-judge. Fits well with the
  `extracted` + `facts_web` pattern you already have.
  - More "pytest-native" alternative: **DeepEval**.
- **Measure**: `faithfulness ≥ 0.9` as a gate; `completeness` over the 7 canonical labels.
- **Caution**: do NOT use the same model as ranker/synthesizer AND as judge — bias. Judge = a
  stronger model (cloud) or a different model.

## G. Quality flag on "poor" games — MEDIUM

- **What**: idea already in `note.md` point 1 — a quality flag before ingest.
- **Why**: today everything enters Qdrant the same. A game with a poor description + no good web
  source pollutes retrieval (noise in the top-K).
- **How**: add `enriched.quality_score` (0–1) computed from signals you already have (number of
  residual `missing_info` after Web, number of sources that passed the judge, presence of the
  structured fields). Threshold for: (a) a stricter re-prompt, (b) a `low_quality` marker in the
  Qdrant payload for downstream filtering, (c) a manual re-enrichment trigger.
- **Measure**: the quality_score distribution over the full catalog; correlation with retrieval
  performance on the below-threshold games.

## H. Model versioning in the evals — LOW (but serious)

- **What**: in `runs/<timestamp>.json` you save `settings.llm_model` (e.g. `"llama3.1"`).
  Ollama can update that pin without you noticing.
- **Why**: the diff vs the previous run becomes misleading if the model underneath changed.
- **How**: also save the weight digest:
  `subprocess.run(["ollama", "show", model, "--modelfile"], ...)` → extract the `FROM <sha>`
  line. Add the `model_digest` field to the payload.
- **Measure**: no metric, it's hygiene for longitudinal comparisons.

## I. Unicode normalization in the quotes — LOW

- **What**: `CuratorEnricher._norm` and `WebEnricher._normalize` only do `lower().split()`. For
  Italian with accents (perché, città, è) and apostrophes (l'avventura) a verbatim match can
  fail while being semantically valid.
- **Why**: a spurious FN due to unicode artifacts (NFC vs NFD, typographic vs ASCII apostrophes)
  → the label ends up in missing for string reasons, not content.
- **How**: `unicodedata.normalize("NFKC", s)` before the lower, and replace the typographic
  apostrophes (`’`, `‘`) with `'`.
- **Measure**: re-scan `runs/last.json` and count the cases where quote and desc differ ONLY by
  accents/apostrophes. Expected: few but real.

## J. Full WebEnricher idempotency — MEDIUM

- **What**: today the cache (`EnrichmentStore`) saves the **fetch**, not the **extraction**.
  Same game + same page + same model = a useless LLM re-call.
- **Why**: if you scale the ingest, every Web re-run redoes the same LLM work. Already flagged in
  `stato.md` § "Where to restart".
- **How**: before calling `_judge_extract` on `(game, url, missing, model)`, look up
  `extractions` by composite key; if already there → skip. After a new call → save.
- **Measure**: ingest time on the second run over the same catalog. Expected: → near zero for the
  Web part.

## K. Cleaning up the "old" tests vs the new structure — LOW

- **What**: `tests/eval.py` and `tests/try_web.py` coexist with the new `tests/eval/<Unit>/`
  structure. They're by the same author, in the same project, doing similar things but in a
  different style.
- **Why**: it confuses newcomers. One of the two perimeters must be chosen.
- **How**: (a) migrate `tests/eval.py` (retrieval on the `core` suite) under
  `tests/eval/Retrieval/` with the same classes+conftest convention; (b) decide whether
  `try_web.py` is a *script* (move to `seller/scripts/`) or a test (same migration).
- **Measure**: none, it's housekeeping.

## L. User memory + chat tier-routing — future (LOW today)

- **What**: the whole `note.md` block on the user profile (`preferred_players`, `loves`/`hates`,
  `past_games`, `skill_level`) + GUIDED/EXPLANATORY/DISCOVERY/QUICK_MATCH strategies +
  Haiku→Sonnet escalation.
- **Why**: it's the next "scope jump" beyond ingest. Orthogonal to everything above but with
  dependencies: it needs tracing (B), it needs multi-provider transport (E).
- **How (high-level, to refine)**: **LangGraph** here YES (state, loops, conditional routing).
  User memory in Qdrant as a separate `user_profiles` collection with an embedding of the
  profile + last-N games visited. Past-chat summary (compression) as a second store. Strategy
  router as a LangGraph node with structured output (`escalate_to_sonnet` field).
- **Measure**: first you need a goal (conversion? engagement? session length?). To be defined
  before touching the code.

## M. Product lineage / flow tracking — HIGH (design to re-discuss)

- **What**: the system cannot answer three operational questions today: *"how are the
  pipelines doing?"* (no run ledger: start/end/failed-count live only in stdout logs),
  *"what happened to game X / why isn't it suggested?"* (its history is scattered: final
  state in `products`, facts in `extractions`, LLM calls in `traces` — which has NO
  `id_product`, so per-game LLM calls are unanswerable), *"how do I retry one product?"*
  (the CLI is all-catalog-or-nothing; `content_hash` skips unchanged games, the opposite of
  a forced retry).
- **Why**: logs are ephemeral (stdout); the durable stores only keep *final state*, not the
  journey. Every "why is this game wrong/missing" investigation is manual archaeology.
- **How (proposed, NOT yet agreed — re-discuss after the Phase 5 review)**:
  1. `product_events` journal table `(id_product, run_id, step, status started/done/failed,
     error, duration_ms, created_at)` written by `EnrichmentPipeline.run` (it already times
     every step);
  2. `pipeline_runs` summary table `(run_id, started_at, finished_at, games_total, done,
     failed, status)`;
  3. `id_product` column in `traces`: enrichers pass `{"id_product": …}` as LangChain
     per-invoke metadata, the callback handler records it;
  4. retry CLI: `python -m app.ingestion.ingester --game <id> --force` (bypass
     `content_hash`, single upsert);
  5. `GET /debug/games/{id}`: one endpoint assembling the whole story — curated record,
     events, extractions with sources, LLM calls, indexed-in-Qdrant status.
  Steps 1–3 are one cohesive commit; 4–5 a second one.
- **Measure**: time to answer "what happened to game X" (minutes of archaeology → one
  query/endpoint call); a retry of a single failed game without re-running the catalog.

## N. Adaptive source count in the WebEnricher — MEDIUM (idea only, do NOT build yet)

- **What**: today `max_sources` is a fixed cap (3): the loop fetches until the cap or until
  `missing_info` is empty. Make the number of sources **adaptive between a min and a max cap**,
  driven by the results: if the first sources filled everything and passed the judge cleanly,
  stop early; if what came back is sketchy (low judge pass-rate, few extractions per page,
  gaps still open), keep widening the pool hoping the sources *together* form a more cohesive
  picture.
- **Why**: a fixed cap spends the same budget on an easy game and a hard one. The easy game
  wastes LLM calls on pages it doesn't need; the hard game gets cut off exactly when more
  evidence would help. The cost (`judge_extract` per page) should follow the difficulty.
- **How (sketch)**: keep the hard floor/ceiling (`min_sources`/`max_sources`); after the floor,
  the stop condition becomes a quality signal instead of a count — candidates already exist:
  residual `missing_info`, judge pass-rate, extraction yield per fetched page (the same
  signals as the quality flag, idea G). No new infrastructure, it's a smarter loop guard in
  `WebEnricher`.
- **Measure**: per-game fetched-sources distribution (expected: bimodal — rich sheets stop at
  the floor, poor sheets reach the ceiling); LLM calls saved on the full catalog vs the fixed
  cap; `n_extractions`/recall on the poor-sheet games must not get worse.

---

## Red lines I would NOT change

A short list of current choices that, if revisited, should be revisited by **measuring**, not
"because I read a blog post":

- **Linear Enricher pipeline** (not LangGraph) for the ingest — correct, the workload is linear
  batch with zero shared state between different steps of the same game.
- **Two-store: regenerable Qdrant + durable SQLite** — this is enterprise IR textbook. No
  "everything in Qdrant".
- **Immutable `original` + `enriched` working copy** — an invariant that lets you reconstruct any
  step. Don't sacrifice it for "simplicity".
- **Citation-grounded extraction with verbatim validation** — it's THE anti-hallucination
  pattern of 2025. Don't replace it with "trust the model" even as the model improves.
- **Unit (FakeLLM, offline) vs eval (real LLM, `llm` marker)** — correct separation, don't merge
  them "for CI convenience".
- **Slot-filling F-β + record/replay for the LLM steps** — it's the right measure of the task.

---

## When to re-read this file

- Before deciding the **next step** after a session (usually: measure → next idea).
- When one of the `runs/` shows an unexplained regression → check section H (model versioning).
- When deciding to go to cloud → sections E + B together.
- When writing the SynthEnricher → section F **before** writing it, not after.
