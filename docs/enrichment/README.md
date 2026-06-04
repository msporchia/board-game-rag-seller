# Enrichment pipeline

Why this exists, in two parts:

**The input is messy.** The source catalog is heterogeneous and incomplete: some games have
clean structured fields, others are a wall of marketing, and the useful facts are scattered
across fields, free-text, and multiple source descriptions — or missing entirely. Fed raw to
the system, games with gaps get mis-weighted, dropped, or compared unfairly with the
well-described ones.

**Retrieval quality is decided by the text we embed**, not only by the embedding model. A raw
marketing description ("epic legendary adventure") flattens into a vague centroid — so a search
for "cooperative dungeon crawler" can't tell the right game from the wrong one.

Enrichment is the set of steps that **turn that messy, heterogeneous input into uniform, dense,
factual, search-friendly records** before they are embedded (*representation engineering*).
Each step should add signal; none should invent.

This folder documents **what each step does and how we know it works** — not the code. One
file per step, in pipeline order. For the code, see `app/ingestion/enricher/`.

## The data we carry per game

The pipeline works on one record per game with a few clearly-separated fields:

| Field | Meaning |
|-------|---------|
| `original` | the hard-truth from the source (catalog DTO). **Never modified** — so we can always verify against it. |
| `enriched` | the working copy the steps fill and transform. |
| `extracted` | facts the steps pulled out of the text (setting, genre, audience…), kept aside for later synthesis. |
| `missing_info` | what we still don't know about a game → tells the Web step what to look for. |
| `embed_text` | the final text that actually gets embedded. The whole pipeline exists to make this good. |

The golden rule across every step: **certain data always wins**. If the catalog states the
player count, no LLM guess can override it.

## The chain

```
Source(DTO) → Curator → Web (fallback) → Synth → Compose → embed_text → vector store
```

| # | Step | What it does (one line) | Status |
|---|------|-------------------------|--------|
| 1 | [Curator](01-curator.md) | reads the description, decides what we know / can extract / are missing — no invention | ✅ implemented |
| 2 | [Web](02-web.md) | for what's still missing, searches the web and extracts verified facts (fallback) | ✅ implemented |
| 3 | [Synth](03-synth.md) | rewrites the description (setting/theme/genre + web facts) so the extractions reach the embedded text | ✅ implemented |
| 4 | [Compose](04-compose.md) | turns the enriched fields into the final `embed_text` | ✅ implemented (rule-based) |

Steps 3 and 4 share the work cleanly: **Compose** owns the structured facts (players, duration,
complexity, tags — deterministic, from the fields), **Synth** owns the descriptive prose (setting,
theme, genre + recovered facts with no field). Each fact appears once, produced by the layer that
does it most reliably.

Three more steps exist only as stubs (`ExtractEnricher`, `AugmentEnricher`,
`GapFillEnricher`) — placeholders for future work, not yet wired in.

> **The link that closed the loop.** The Curator's extractions live in `extracted`, but Compose
> builds `embed_text` only from the `enriched` fields — so until **Synth** wrote them back into
> the description, the recovered setting/genre/web facts never reached the embedding, and no
> pipeline beat the raw baseline. With Synth in place, `curator → synth → compose` is the **first
> pipeline to beat it** on the `core` suite.

## How we evaluate

We decide with numbers, not intuition. Three levels, each with a different job:

1. **Unit tests** (offline, deterministic, fast). Contracts and invariants — "hard-truth stays
   intact", "certain data wins", "a fact is kept only if its quote is verbatim in the text".
   The LLM is faked, so these are reproducible and run on every change.

2. **Per-step quality eval** (uses the real LLM, slow). Measures **one step's goal in
   isolation**, against a hand-written **oracle** (an answer key). We measure steps separately
   on purpose: an end-to-end average hides *which* step gains and which loses. Each step file
   below explains its own metric.

3. **Retrieval scorecard** (end-to-end). Re-ingests a frozen corpus and runs real queries.
   The verdict is the **rank, not the absolute score**: cosine similarity is uncalibrated
   (the gap between a perfect and a wrong match can be ~0.06), so "70%" means nothing. What
   matters is whether the right games rank **above** the wrong ones — measured with Recall@K,
   Precision@K and inversions, against frozen relevance labels. See `docs/valutazione.md`.

Two principles worth repeating:
- **The oracle is never fed to the system.** It's the answer key; using it as input would be
  testing on the answers.
- **Oracles are partial by design.** We assert only what we're sure of, and grow the answer
  key as we find cases the system gets wrong.

## Running the evals

```bash
# Per-step quality (real LLM, slow — minutes per case on CPU):
docker compose exec seller-api python -m pytest tests/eval/CuratorEnricher -q
docker compose exec seller-api python -m pytest tests/eval/WebEnricher/test_ranking.py -q     # deterministic, no LLM

# Quick iteration: run only the first N cases instead of the whole suite
docker compose exec -e EVAL_LIMIT=2 seller-api python -m pytest tests/eval/CuratorEnricher -q

# Retrieval scorecard (compare pipelines on the frozen 'core' suite):
docker compose exec -e PYTHONPATH=/app seller-api python tests/eval.py --suite core --k 5 --pipeline rule
```

> Tip: the LLM steps are slow on CPU (an 8B model). Enable the GPU override
> (`docker-compose.gpu.yml`) or use `EVAL_LIMIT` while iterating.
