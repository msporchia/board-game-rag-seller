# Seller project status — handoff

Restart point. For details: `pipeline-dati.md` (architecture/data), `valutazione.md` (how we
measure), `note.md` (ideas), `seller.md` (overview).

## What exists (built and working)

- **Docker**: `catalog-mysql` (catalog snapshot), `catalog-ps` (local PrestaShop browsable at
  http://localhost, classic theme), `seller-qdrant`, `seller-ollama`
  (`nomic-embed-text` + `llama3.1`, **GPU enabled** — 50/50 offload, limited by the VRAM the
  desktop already uses), `seller-api` (FastAPI).
- **PrestaShop export**: `controller=seller` + `SellerExporter`/`SellerProduct` (in the PHP
  Seller module, out of this repo) → enriched DTO. Includes `source_descriptions`: **all** the
  per-source descriptions from a product-info table (one row per source, cleaned+deduped).
- **Python microservice** (`seller/app/`):
  - `ingestion/sources.py`: `PrestashopSource`, `JsonSource` → `GameDoc`.
  - `models.py`: `GameDoc` = `original` (hard-truth) + `enriched` (working copy) +
    `embed_text` + `missing_info` + **`extracted`** (info extracted from the description/web,
    produced by Curator and Web → consumed by the SynthEnricher); `GameData` (flat shape, with
    `source_descriptions`); `GameHit`.
  - `ingestion/enricher/` (one file per enricher): `base`, `trim` (FAILSAFE 1000 chars),
    `compose` (`RuleComposeEnricher`), `curator` (`CuratorEnricher` — citation-based, NO
    synthesis), `web` (`WebEnricher`), stubs `extract`/`augment`/`gapfill`.
    **Unified synthesis step** (`SynthEnricher`) still TODO.
  - `core/web_search.py`: `DdgsSearch` (DuckDuckGo search, swappable) + `fetch_clean`
    (httpx with browser User-Agent + trafilatura).
  - `core/enrichment_store.py`: `EnrichmentStore` (SQLite, durable system-of-record).
  - `ingestion/serializer.py` (`DocumentSerializer`), `core/vector_store.py`
    (`GameVectorStore`), `ingestion/ingester.py`, `rag/retriever.py`, `api/` (`/health`, `/search`).
- **Tests** (pytest, one folder per unit `tests/<unit>/<ClassName>/`, **one class per file**
  with an opening docstring of purpose/what-it-tests/how):
  - `tests/unit/` (**115 pass**, DETERMINISTIC, no Ollama/Qdrant): contract/invariants of each
    step. LOCAL fixtures in each unit's `conftest.py` (`make_curator`, `store`, `make_web`);
    cross-unit helpers (`make_game`, `FakeLLM`) in `tests/factories.py`. For the LLM steps the
    model is faked: `CuratorEnricher/` (test_enrich = hard-truth intact, certain data wins;
    test_assess = contract over **10 REAL DTOs** from the core suite + fail-safe parsing;
    test_prompt_builders = pure functions), `WebEnricher/` (test_guard, test_discovery =
    ranking, test_extraction = **anti-hallucination**: a fact is kept only if the quote is
    verbatim in the text).
  - `tests/eval/` (some require Ollama, marker `@pytest.mark.llm`, excluded from the unit run):
    measures each GOAL in isolation. `CuratorEnricher/test_assess.py` (job C: no false-missing
    on the certain fields, over 10 REAL DTOs from the `core` suite, partial oracle per game).
    `WebEnricher/` = **record/replay PER PHASE** (3 steps measured separately): `recorder.py`
    freezes `search_results` (DDG) and `pages` (curl) per game once; `test_ranking.py`
    (no-LLM, deterministic) checks `top_domains` and `must_drop_domains`; `test_judgment.py`
    (LLM) checks `is_this_game`/`is_serious` per URL; `test_extraction.py` (LLM) checks that
    the fact is extracted with `value_contains` + a verbatim quote in the text. The oracle
    (`expect.{ranking,judgment,extraction}` in the fixtures) is PARTIAL by design — we assert
    only what we're sure of.
  - `tests/eval.py` (retrieval, suite `core`, pipeline `rule`/`trim`/`curator`),
    `tests/try_web.py` (manual end-to-end WebEnricher run).

## Enrichment pipeline (current architecture)

```
Source(DTO) → CuratorEnricher → WebEnricher(fallback) → [SynthEnricher TODO] → RuleComposeEnricher → serializer → Qdrant
                  │                    │                          │
                  │                    │                          └─ unified synthesis over certain data +
                  │                    │                              extracted + multi-source source_descriptions
                  │                    └─ runs ONLY if gaps remain (game.missing_info)
                  └─ classification + extraction (citation-based with verbatim validation)
            EnrichmentStore (SQLite) ← persists each game's curated record
```

- **CuratorEnricher** (llama3.1, **citation-based**): for each of the 7 REQUIRED INFO it asks
  the LLM `{where: CERTAIN_DATA|TEXT|NONE, quote: verbatim, normalized_value}`; it **validates
  the quote** post-hoc in code (it must be verbatim in the material, otherwise it degrades to
  NONE — anti-hallucination). It derives the canonical output `{estratti, presenti, mancanti}`.
  Reduced scope: it NO LONGER synthesizes the description (it did in v1, and it proved harmful
  — the synthesis now lives in the downstream `SynthEnricher`, with ALL the material). The
  `estratti` are saved to `GameDoc.extracted` for the Synth.
- **WebEnricher** (FALLBACK, **non-agentic, hybrid**): mini-RAG with verification — clean name
  → DDG search → ranking (blocklist drops retailers/our own shop; whitelist first) → fetch with
  UA (cached on the store) → **LLM judgment** relevance/seriousness → **quoted extraction** →
  **validation** (same pattern as the Curator: is the quote really in the text? otherwise
  discard) → applies it with provenance. Whitelist/blocklist in `config.py`.

## Two separate stores (architectural decision)

- **Qdrant** = **regenerable** index: vector + **lean** payload. The ingest does
  `force_recreate=True`, so it CANNOT be the persistent memory.
- **EnrichmentStore (SQLite)** = durable system-of-record, "the work you don't throw away":
  `products` (curated record: original/enriched/embed_text/missing_info + content_hash),
  `web_pages` (fetch cache → no re-fetching), `extractions` (facts + quote + provenance →
  `source_scoreboard()` = source reliability over time). DB at `/app/data/seller.db` =
  `seller/data/` on the host (persists across recreates, gitignored). The `Ingester` populates
  it (`--no-store` to disable); it's `None` in eval/test.

## Measured results

### Retrieval (suite `core`, K=5)
- Baseline `rule`: **Recall@5 = 0.26**, P@5 0.42, err 0.32.
- `trim` (aggressive 350 chars): **0.19** → the hypothesis "cutting marketing helps" is
  **falsified** (blind trim throws away useful theme words). The default is now a failsafe at
  1000.
- `curator` v1 (with synthesis at ~400 chars): **Recall@5 0.23, P@5 0.38** → does NOT beat the
  baseline. The compressed synthesis lost theme words (same lesson as trim). **THE REASON the
  synthesis was MOVED into the SynthEnricher** (with ALL the material available, no longer
  blind compression of the description alone).

### Citation-based Curator — eval on 10 curated cases (`tests/eval/CuratorEnricher/`)
LOCAL fixture with TARGETED stripping of structured fields + an explicit per-case oracle
(`must_be_present`, `must_be_missing`, `must_be_extracted`). The suite simulates "no BGG" on
real games (4 structures stripped) to measure what the Curator can recover from the description
alone.
- **v1 (synthesis+extraction+classification in one shot)**: **1/10 PASS**. Pattern: the 8B
  **INVENTED** structured values (unrecognized gap: 6 cases).
- **v2 (schema simplified to 3 keys)**: **0/10 PASS**. It flips: everything into missing.
- **v3 (citation-based + CERTAIN DATA in the prompt + verbatim validation)**: **1/10 PASS**.
  Invention almost gone but the 8B too conservative (quotes strings that fail the verbatim
  match).
- **v4 (no CERTAIN DATA + dynamic list + chunking)**: 3/10 PASS on the boolean assertion.
  Scan: the CERTAIN DATA is present in 49/50 of the production DTOs → useless to pass it to the
  LLM. The LLM works ONLY on the description, asks ONLY the missing labels (3 descriptive always
  + missing structured); chunking at `max_per_call=4`.
- **v5 CURRENT — standard slot-filling scoring** (TAC KBP / TREC IE): oracle extended to ALL 7
  slots per case (structured from the original non-stripped DTO, descriptive hand-curated);
  metric = TP/FP/FN/TN per slot → global Precision/Recall/F1/F0.5/F0.25. No LLM-as-judge
  (requires a powerful model + reintroduces non-determinism): deterministic substring matching.
  **llama3.1 baseline to beat** (45 slots evaluated): Precision **0.654**, Recall **0.515**,
  F1 **0.576**, F0.5 **0.620** (precision-favored 4×), F0.25 **0.644**. Per-slot: setting
  8/2/0; genre 4/1/5; audience 2/3/3; players 2/0/2 (precision 100%); duration 0/2/3 (FP
  "spurious": text contradicts BGG → certain data wins); complexity 1/1/3. Real FP patterns:
  3× "fantasy" default as setting, 3× "families" default as audience, 1× slot confusion.

The report is PERSISTED in `tests/eval/CuratorEnricher/runs/<timestamp>.json` (gitignored): per
case it counts TP/FP/FN/TN per slot, LLM value vs oracle. Aggregate `metrics` (P/R/F-β) + diff
vs the previous run printed at the end of the session. Offline analysis without re-running
(~3 min).

**Direct probe** (no pytest, no code — `curl http://localhost:11434/api/generate`): lets you
iterate on the prompt in 10s instead of 3min. Used to evolve v1→v4.

### WebEnricher
- **Per-phase eval**: `recorder.py` freezes `search_results` (DDG) + `pages` (curl) per game;
  3 parallel tests measure one phase each — ranking (deterministic), judgment (LLM,
  `is_this_game`/`is_serious`), extraction (LLM, `value_contains` + verbatim quote). Change the
  model → only the LLM phases break and the diff says EXACTLY on which URL/info. Fixture:
  `viticulture.json` (a set of ~9 games remains to be added: new/poorly-covered, homonyms,
  retail-heavy, Wikipedia traps).
- **Manual Viticulture run**: for board games **reviews abound** and are richer than the
  publisher's site (4/4 good sources). Italian Wikipedia weak (4/8) **and dangerous** (for the
  missing ones it returns wrong but confident matches: Viticulture→Carcassonne). BGG (401) and
  goblins (403) block bare fetchers but **pass with a browser UA**. **Descriptive** fields agree
  across sources → safe; **numeric** ones (duration, age) **diverge** → cross-verify or "certain
  data".

## Key decisions

- Seller consumes an **API contract**, not the DB. `original` immutable; the enrichers work on
  `enriched`. Compose = a single step (word order matters).
- **Curator: no CERTAIN DATA in the prompt, dynamic list, chunking**: scan over 50 production
  DTOs → structured present in 49/50, so useless to pass it to the LLM (and we apply it
  downstream, it ALWAYS wins). The LLM asks ONLY the 3 descriptive ones (always, not in the
  DTO) + the structured ones that may be missing. Per label it produces
  `{quote, normalized_value}`; the code validates the verbatim quote in the DESCRIPTION
  (anti-hallucination, same pattern as Web). Chunking at `max_per_call=4` for "no-BGG" cases
  (eval). The eval measures the delta of each change with a persistent report.
- **Synthesis moved out of the Curator**: the job-A (description rewriting) now lives in
  `SynthEnricher` (TODO) → it receives `certain_data + curator_extracted + web_facts +
  multi-source source_descriptions` and produces ONE unified synthesis over rich material.
  Advantage: the 8B handles separate tasks better + the synthesis sees EVERYTHING (not just the
  main description).
- Tests: relevance via **tags (qrels)**, verdict on the **rank** not the absolute score;
  **frozen corpus per suite**; test oracle separate from the system.
- **Per-step validation**: each step has its own GOAL, measured separately (end-to-end averages
  and hides who gains and who loses). Deterministic steps → exact invariants; LLM steps →
  invariants with the faked model + quality/choices measured vs oracle/golden, with
  non-deterministic inputs FROZEN (web record/replay). The Curator does 3 jobs (A synthesis, B
  tag deduction, C present/missing classification): retrieval sees only A — the compression,
  which LOSES recall — while C doesn't touch the embedding (it guides the Web) and must be
  measured on its own. So it's not "the step is harmful", but "A must be measured and refined
  (prompt) for what it does".
- **Local** (llama3.1) for now; remotely it only improves.
- **Online enrichment = we say WHERE to look** (whitelist + LLM judgment on unknown domains),
  not agentic: with an 8B, letting it pick the sources is unreliable. Target = **reviews**.
  Cross-verify the numeric ones. Browser UA for the bot-protection.
- **Local multi-source** (`source_descriptions` from the product-info table): export READY, but
  `CuratorEnricher._collect_descriptions` is **NOT wired in** (on purpose: the Curator uses the
  main description = "we already have the top"). The VALUE of multi-source must be measured **at
  scale** (1000+ games: how often does it actually add something?) before wiring it.
- **LangGraph**: NO for the ingest pipeline (linear/batch); YES for the future chat
  (state/loops/routing/escalation). LangGraph's checkpointing ≠ the EnrichmentStore.

## Where to restart

- **SynthEnricher (NEXT)**: implement the unified synthesis step. Input: certain data +
  `game.extracted` (from the Curator) + facts from the Web + **multi-source
  `source_descriptions` (not wired in yet, the API already exports them)**. Output:
  `enriched.description` = unified synthesis (~400-600 chars) based on ALL the material (no
  longer on the main description alone). Deterministic unit tests + FIDELITY eval vs oracle.
- **Curator — the last fine errors**: at 3/10 PASS, the 7 residual fails are micro errors
  (1 label out of 7) — no longer catastrophic. Pattern: (a) "genre" mis-recognized (4/7),
  (b) "complexity" gap-detected when the 8B quotes a plausible word, (c) 1 sub-optimal extracted
  value ("1-4" vs "2-4"). Hypothesis: hard-code "genre" derived from the DTO's `categoria` field
  (always present, sub-category ≈ genre); or change the model (Qwen2.5 / Gemma) and measure the
  delta with the `runs/` diff.
- **Retrieval**: the Curator doesn't beat the baseline yet; the next retrieval test must be done
  AFTER the SynthEnricher (it's the synthesis that enters `embed_text`). Hypotheses to try: a
  compose that KEEPS dense tags/themes + synopsis; multilingual embedder (`bge-m3`) vs `nomic`
  (weak on Italian).
- **Full real loop**: Curator → Web → Synth → Compose on real games with the store enabled, to
  see curated data + provenance accumulate.
- **Full WebEnricher idempotency**: reuse the already-saved `extractions` to skip the LLM
  re-call (the cache currently saves only the fetch).

## Useful commands

```
docker exec seller-api python -m pytest tests/unit -q                       # deterministic unit (offline, 115 pass)
docker exec seller-api python -m pytest tests/eval/CuratorEnricher -q        # classification+extraction eval (LLM, ~3-5 min)
                                                                              # → persistent report in tests/eval/CuratorEnricher/runs/
docker exec seller-api python -m pytest tests/eval/WebEnricher/test_ranking.py -q       # ranking phase (no LLM)
docker exec seller-api python -m pytest tests/eval/WebEnricher/test_judgment.py -q       # judgment phase (LLM)
docker exec seller-api python -m pytest tests/eval/WebEnricher/test_extraction.py -q     # extraction phase (LLM)
docker exec seller-api python -m tests.eval.WebEnricher.recorder --slug <s> --name "<game>" --missing "ambientazione,durata"
                                                                              # records real search+pages; then fill in `expect` by hand
docker exec seller-api python -m tests.eval --suite core --k 5 --pipeline curator   # retrieval ablation
docker exec seller-api python -m app.ingestion.ingester --max-pages 2   # ingest + store
```
