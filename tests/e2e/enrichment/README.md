# E2E — Enrichment

End-to-end of the **enrichment part only** (not the whole product): from a few games' base data
(taken from the frozen corpus) to queryable embeddings, running the **real** production pipeline
(Curator → Web → Synth → Compose) with real LLM and embeddings, on throwaway stores.

Philosophy: everything is real except what we don't control — **the web**. Scraping is frozen and
pinned to recorded fixtures; any unexpected network attempt fails the test (see `rails.py`). The
point of the e2e isn't just to pass: it's to **expose** how the pieces actually behave together.

## How to run

Needs the containers (Ollama + Qdrant). Not part of the offline unit run (`pytest.ini`
`testpaths = tests/unit`): launch explicitly.

```bash
# the whole e2e suite (3 phases + regression gate, one shared ingest)
docker exec seller-api python -m pytest tests/e2e/enrichment -v

# ingest + scorecard + baseline diff, by hand (gate via exit code)
docker exec seller-api python -m tests.e2e.enrichment run

# rewrite the baseline after an intended improvement, then COMMIT baseline.json
docker exec seller-api python -m tests.e2e.enrichment run --update-baseline

# re-record the frozen scraping (network, once) when adding a game or refreshing sources
docker exec seller-api python -m tests.e2e.enrichment record --ids 160,22,21
```

## Architecture (one class, one job)

| module | class | job |
|---|---|---|
| `cases.py` | `GameCase` | the declarative case: corpus DTO + recorded scraping + oracle |
| `rails.py` | `Rails` | pins the web: query-routed provider + page-cache seed + fetch guard; derails on any unexpected network |
| `harness.py` | `EnrichmentHarness` → `RunResult` | the single real ingest (full + base + distractors) on throwaway stores |
| `scorecard.py` | `Scorecard`, `Baseline` | run metrics + improved/regressed gate vs the versioned `baseline.json` |
| `recorder.py` | `Recorder` | freezes the scraping (live web → fixtures), preserving the oracle |
| `__main__.py` | — | single CLI: `record` \| `run [--update-baseline]` |

The three phases share **one** ingest (`conftest.ingest`, session-scoped); the `Scorecard` derives
the metrics from it.

1. **`test_phase1_ingest`** — the ingest runs whole, the DB populates, and the scraper stays **on
   the rails**: the Web fires *only when it should* (`expect_web` per game) and no query/URL leaves
   the fixtures.
2. **`test_phase2_data`** — data in the **right places**: `original` immutable; structured facts in
   `embed_text` as deterministic sentences (exact check); descriptive facts in `extracted`; Web
   extractions with verbatim quotes (anti-hallucination).
3. **`test_phase3_retrieval`** — embeddings are **good**: common queries retrieve the game in the
   first screen; enrichment recovers poor DTOs; Synth regression documented (xfail).
4. **`test_regression`** — the **gate**: no gate metric regresses beyond tolerance vs the
   versioned baseline.

## Games and scraping

Games come from the frozen corpus (`tests/fixtures/suites/core/games.json`); each has a
`fixtures/<slug>.json` with **recorded** scraping (`search_results` + `pages`) and a hand-written
**oracle**. They are the games already battle-tested by the WebEnricher fixtures: **Onitama**
(160), **Viticulture** (22), and a third profile, **Terraforming Mars** (21).

`strip_certain` in the oracle blanks some certain DTO fields **before** ingest to "encourage" the
Web (the Curator can't fill a gap that isn't in the data → it lands in `missing_info` → the Web
goes online). So we exercise the scraper on poor-sheet games and verify, on rich-sheet games, that
the Web correctly does **not** fire.

## Retrieval is a *first screen* (why the thresholds look like this)

Phase 3 measures **recall in the first screen**, not fine precision. Rationale — keep it in mind
when we build the product's retrieval/refinement layer too:

- Vector search on a large catalog (hundreds of games) is for **screening**: from N games pull a
  candidate set of ~10-20 plausible ones. It needn't nail the fine order.
- So what matters is that **queries as a user types them** ("a two-player martial-arts game") bring
  the game *into* the screen — not that the text contains a detail keyword (e.g. "oceans"). A user
  rarely searches "a game about the ocean"; that detail is re-read by the **LLM after fetching** the
  candidates, with full context.
- **Fine refinement** (setting, duration, ...) is a **later, dynamic LLM step**: "refine? which
  setting do you prefer? does duration matter?", as aggressive as the screening needs. Not the
  embedding's job.
- Hence `SCREEN_K` is wide and the metrics are recall-based: if out of 500 games we return 10 and
  the target is among them, screening worked, regardless of the rest of the set.

Consequence: if the vector comfortably holds more text, the Synth-over-compression problem (see
`docs/enrichment/e2e-findings.md`) is "just" a Synth fix — not a retrieval limit.

## Regression baseline (improved/regressed) and CI

`baseline.json` is **versioned on git**: the metric snapshot of the last "good" state. Every run
recomputes and compares with **tolerances** (the LLM/embeddings aren't bit-deterministic). The gate
rides on robust metrics — `web_fired` (exact) and recall@K (queries reaching the screen, tolerating
a 1-query wobble); raw ranks are noisy and kept informational. A gate regression fails the suite.
When you intentionally improve the pipeline, `run --update-baseline`, commit the new
`baseline.json`, and git history becomes the quality trend.

### Suggested CI staging (test pyramid)

Make *what runs* a choice of whoever writes the CI triggers — parametrize by marker:

- **Every merge request** → the fast offline unit run (no containers):
  `pytest` (defaults to `tests/unit` via `pytest.ini`).
- **Merge to `main` / nightly** → the e2e (needs `docker compose up` for Ollama + Qdrant):
  `pytest tests/e2e -m e2e`. Heavier (~2 min) but it's where the regression gate lives.

This mirrors the standard pyramid: many fast unit tests guard core changes on every MR; few slow
integration/e2e tests guard quality on the trunk. Markers are declared in `pytest.ini` (`e2e`,
`llm`) so selection is explicit.
