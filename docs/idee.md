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

## O. Strategy routing as configurable policy (A/B tests, user groups) — IMPLEMENTED (generalized to a policy middleware seam)

- **BUILT (2026-06-17)**: shipped broader than this section asked. Instead of only making the
  route node's `pick_strategy` swappable, the turn now carries a `custom_policy: [name, ...]`
  list (API → `ChatState`); `PolicySet` resolves each name to a `Policy` class (the wiring lives
  in `app/chat/policies/`, the concrete policies one-per-file in `app/chat/policies/library/`,
  hardcoded `REGISTRY`, unknown names logged-and-skipped) and composes them
  as **middleware** around the `retrieve` and `generate` stages (`around_retrieve`/
  `around_generate` + the `force_expertise`/`force_strategy` shortcuts). A policy is open code: it
  can reshape the query/filters/hits, inject prompt blocks, swap the retriever, or replace a stage
  — not a closed knob set. Starter policies: `christmas_sale`, `promote_cooperative`,
  `assume_advanced`, `force_quick_match`. The active names are logged per node (measurability),
  and each policy's effect is unit-tested in isolation so it stays stable across prompt changes.
  Still future (the original §O scope): variants keyed by experiment arm + user group loaded from
  config/store, sticky-per-session arm assignment, arm recorded in `traces`, and an outcome metric.
- **What**: today `pick_strategy` is fixed first-match-wins rules in code. The expectation is
  that this logic grows and churns: marketing will change the selling rules often, and we'll
  want **A/B experiments** and **per-user-group variants** (different personas/strategies per
  customer segment). The graph shape stays; the *policy* inside the route node must become
  swappable without a rewrite.
- **Why**: rules-in-code means a redeploy per marketing change and no way to compare variants.
  This is also the argument that justifies LangGraph here long-term: the topology is the stable
  part, policies are the volatile part.
- **How (sketch)**: extract the routing policy behind a class injected into ChatGraph (it
  already takes everything via constructor); variants keyed by experiment arm + user group,
  loaded from config/store; the arm assignment is sticky per session (it lives in the
  checkpointed state); arm + chosen strategy recorded in `traces` so outcomes are measurable.
  Same later for the prompt rule-sets (`_STRATEGY_RULES`).
- **Measure**: an A/B needs an outcome metric FIRST (see §L: conversion? clicks on cards?
  turns-to-proposal?). Without it, this stays an idea.

## P. Concurrent requests on the same session — LOW

- **What**: two simultaneous `POST /chat` with the same `session_id` (double click, frontend
  retry) read the same checkpoint and both write: last-writer-wins, one turn silently vanishes
  from the session memory.
- **Why**: the failure is silent and looks like "the bot forgot". Expectation: the **frontend
  serializes** (disable input while a reply is pending) — this is the contract. Server-side
  hardening is a future nicety, not a now-problem.
- **How (later)**: document the contract on the endpoint; if it ever bites, a per-session_id
  in-process lock (or an optimistic version check on the checkpoint) is enough — no
  distributed locking until there are multiple API replicas.
- **Measure**: none — robustness. A unit test with two interleaved turns documents the limit.

## Q. Tiered chat engine: agentic retrieval behind the pipeline — MEDIUM (seam + tool + agent STUB built)

- **BUILT (2026-06-17, groundwork)**: the `search_catalog` tool (`app/chat/tools/`, wraps
  GameRetriever+SearchFilters, reuses `SearchIntent` as the arg schema) and `AgenticChat`
  (`app/chat/agentic.py`) now exist: the strong model `bind_tools`-drives the search in a bounded
  loop, and the grounded answer is still `ChatAdvisor.pitch` over the UNION of the tool's hits —
  the three invariants stay in code at the boundary as below. Wired behind `engine=agent` into
  TieredChat's primary slot (the empty slot this section described). STUB: per-turn/stateless (no
  history yet), no click→filter merge, no circuit breaker — exercised offline with a fake
  tool-calling LLM; the local 8B can't drive tools, so it degrades to the pipeline fallback.

- **What**: two chat engines behind one stable contract (`reply(message, choices, k,
  session_id) → ChatResponse`): today's decomposed pipeline (weak local model, every decision
  in code) and a future **agentic** engine — strong model, a `search_catalog` tool wrapping
  GameRetriever+SearchFilters, the model decides *when and what* to search, iterating.
  `TieredChat` (app/chat/tiered.py — BUILT, primary slot empty) is the seam: a primary that
  MAY fail wrapped over a fallback that must not.
- **Why**: the ChatConversation eval showed the convergence misses are partly structural —
  GUIDED never re-retrieves on text-borne refinements, the model has no agency over retrieval.
  An agent fixes the *class* of failures, but llama3.1-8B can't drive tools reliably, so the
  tier must be optional and safely degradable. Note the cost asymmetry: a failed agent turn is
  the MOST expensive turn (N tool loops on the strong model + timeout + then the pipeline) —
  the circuit breaker below is what makes the wrapper viable, not an optimization.
- **How (when the agent exists)**:
  1. the three invariants stay in CODE at the boundary, identical for both engines: grounding
     validated against the **union** of everything the agent's tool calls returned, the
     ChatReply/ChatResponse contract, the honest no-match + deterministic fallback;
  2. **ChatState stays the lingua franca**: the agent reads history/filters_spec in, writes
     them back out — this is what makes any single turn servable by either engine, i.e. what
     makes per-turn fallback possible at all;
  3. failure = mechanical criteria only: tool-loop budget (2-3), timeout, final output not
     validating the schema, zero grounded ids. Deterministic failures (schema, grounding)
     weigh more in the breaker window than transient ones (timeout, transport);
  4. **circuit breaker** in TieredChat: sliding window of primary outcomes → open (skip the
     primary entirely, no wasted call) → half-open probes after a cool-down (1 turn in M) →
     close on recovery. Hysteresis prevents flapping;
  5. rollout ladder: `CHAT_ENGINE=pipeline|agent|auto` env switch (structural decisions,
     human, hours) above the breaker (incidents, automatic, seconds) above the per-turn
     budget (milliseconds); ramp-up — shadow replay of real sessions scored offline, then A/B
     by session hash, canary on escalated sessions first (the `escalate` signal generalizes
     from "swap the model on one node" to "swap the whole path"; see §L tier-routing, §O
     swappable policies).
- **Candidate primary model**: `gpt-oss:20b` (agentic-native, open weights, runs on the dev
  box with RAM freed; `qwen3:14b` as the lighter alternative). NOT to be tested by swapping it
  into the pipeline slots as a fix — the convergence failures are architectural (re-retrieval
  condition, GUIDED k, embedder paraphrase gap) and a stronger model in the same cage fixes
  none of them. The experiment that matters is the unified tool-calling prompt: the agent's
  unique value is deciding WHEN to search and WITH WHAT WORDS (it translates customer
  paraphrase into catalog language — the lexical gap the embedder can't bridge).
- **Arm B — the code-piloted agent loop (weak model, build BEFORE the autonomous agent) —
  BUILT and measured (app/chat/piloted.py, selector `CHAT_ENGINE=pipeline|piloted` +
  per-request `engine` override; 2026-06-12, ChatConversation)**:
  same loop shape as the agent, but the graph orchestrates and the weak model does one
  constrained job per step. Each turn: (1) the model expresses its recommendation INTENT as
  structured output ("I'd suggest something like…": query + extracted constraints — the
  generate-then-retrieve / HyDE family: the query becomes the model's reformulation, never
  the user's verbatim text); (2) code fetches with it (clicks stay hard filters, code-managed
  — the model proposes, the code disposes); (3) zero/poor results loop back explicitly:
  "this path returned nothing — reformulate, or tell the customer honestly?" — the no-match
  becomes informed (the model SAW the result count) instead of guessed from a k-sized list.
  Subsumes the planned re-retrieval fix (searching every turn on fresh intent replaces the
  smarter skip-condition) and fixes the paraphrase gap with the weak model. Costs to measure:
  +1 LLM call per turn, +1 per retry; risk: the 8B reformulation losing user constraints —
  hence structured query + code-side filter merge. This is also why today's design can't
  answer "is game X in the catalog": absence-from-hits ≠ absence-from-catalog; arm B's
  explicit result count is what makes honesty knowledge instead of luck.
  **Measured (same fixtures, pipeline run then piloted run, llama3.1 both, 2026-06-12)**:
  case pass 0.700 → **0.800**, convergence 5/8 → **6/8**; cost 43 → 47 LLM calls (+4: the
  zero-result retries actually firing) and 56 992 → 46 726 tokens (−18%: the intent prompt is
  leaner than the analyze rubric). Δquality/Δcost: +0.100 case pass for +4 calls and −10k
  tokens. Per failure class: *terraforming* RECOVERED (turn 2 — fresh intent re-retrieves on
  the text-borne refinement) and *contrordine* RECOVERED (turn 1 — the model declared age=8
  and it became a hard filter; request-k replaced GUIDED's k=2). *pandemic* moved, not fixed:
  the reformulation ("gioco cooperativo per famiglie…, senza vincitori e vinti" + age≤8) DID
  put Pandemic 10th Anniversary on the table (hit 3 of 5 — the paraphrase gap closed as
  designed), but the PITCH step picked Fairy Tile/Fantascatti off the table — the failure
  migrated from retrieval to generation, outside arm B's loop. One REGRESSION, the predicted
  one: *carcassonne-cliente-deciso* (title lookup) — the intent step abstracted "Carcassonne"
  into a generic description AND invented players=2/max-30-min constraints; its own invented
  duration filter excluded Carcassonne (45 min). The 8B losing/inventing constraints is now a
  measured failure mode, not a hypothesis; next experiments: keep customer-named titles
  verbatim in the query (title-availability as its own intent shape), and judge the pitch
  pick separately from retrieval (the pandemic lesson).
- **Measure**: ChatConversation is the arbiter — same fixtures, swap the `graph` conftest
  fixture, compare RESULTS deltas. THREE arms, not two: today's pipeline (baseline) vs the
  piloted loop (arm B, weak model) vs the autonomous agent (arm A, strong model). Same loop
  shape between A and B means the A-vs-B delta isolates "who drives" from "model quality";
  running the strong model in the pipeline slots ONCE stays the control group for
  caged-vs-free. That attribution — how much is architecture, how much is model — is the
  finding to record.
  In production the guard metric is the primary-degradation rate per window: above threshold
  the breaker opens on its own; open for days means "wrong model", i.e. an env-level decision.
- **Operational pattern (industry-grounded)**: the three arms COEXIST in code behind a
  selector — `CHAT_ENGINE=pipeline|piloted|agent` env default + an optional per-request
  `engine` override on ChatRequest (what makes shadow runs and tests possible without env
  churn) — BUILT for pipeline|piloted (app/api/chat.py: one TieredChat per arm, the selected
  engine primary over the pipeline fallback, ONE shared checkpointer).
  **Known limitation, not yet fixed (documented on purpose)**: degradation is NOT transactional.
  LangGraph persists per super-step, so a primary that raises *after* a partial write (e.g.
  piloted's `_intent` already appended `"utente: …"` to `history`) leaves a dirty checkpoint the
  fallback then resumes on the same `thread_id` — duplicating the history line and leaving stale
  scratch channels (the latter reset by the next turn's `_intent` anyway). Today the two piloted
  LLM steps are internally try/except'd, so the uncaught window is narrow (Qdrant down in
  `_search`, `pitch` internals) and the impact is cosmetic; no test covers it yet. The fix when
  it matters: TieredChat snapshots the thread's checkpoint before the primary and restores it on
  exception before the fallback (all-or-nothing per turn), paired with logging the degradation
  cause (`exc_info`, today a bare `log.warning`). A pivot is a config flip plus a later dedicated removal commit, never a git revert.
  Measurement grammar: one goal metric (convergence/case-pass) + guardrail metrics that must
  not regress (tokens/conversation, LLM calls/turn, latency, fallback rate) — the deciding
  number is Δquality/Δcost, never Δquality alone. Instrumentation: `traces` gains an engine
  tag + token counts (Ollama's prompt_eval_count/eval_count via usage_metadata), so
  cost-per-conversation-per-arm is one query; ChatConversation records LLM calls + tokens per
  conversation so RESULTS compares arms with the cost denominator inline — the suite half is
  BUILT (LLMUsageTracker + engine-tagged runs); the `traces` engine tag is still to do. Endgame per the
  cascade/router literature (FrugalGPT, RouteLLM): the arms are TIERS of a cascade routed per
  turn — `escalate` is the embryonic router — not three alternative futures.
- **Client-closed conversion loop (STRUCTURAL, build the seam from day one)**: conversions
  (card click, add-to-cart, purchase) happen in the CLIENT, so the A/B must close through the
  contract. Arm assignment is server-side and sticky per session (deterministic hash of
  session_id over config weights — reweighting never redeploys the client); the per-request
  `engine` override stays as a QA/shadow tool only. ChatResponse ECHOES the assigned arm: the
  client doesn't choose it, it reports it back on its analytics events together with
  session_id — a two-field client contract. Ingestion: storefront analytics joined on
  session_id, or a minimal `POST /events` (session_id, type, id_product) → events table; with
  arm-tagged traces and per-turn last_recommended_ids, conversion-per-arm (even per card
  position) is one query. The assigner sits in front of engine selection from day one, even
  with one arm at 100% — adding an arm becomes config. Two-level OEC: offline stays
  ChatConversation convergence (cost guardrails), online becomes conversion per arm. Same
  mechanism §O needs for strategy-policy experiments — build once, reuse.

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
