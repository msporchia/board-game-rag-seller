# 0001 — Enrich the embedded text, instead of reaching for a stronger embedder

**Status:** Accepted · recorded post-hoc 2026-06-19

## Context

The catalog is heterogeneous and incomplete: some games arrive richly described, many as little
more than a name and a few structured fields. Fed raw to an embedder, that difference *becomes*
the ranking — a thin record sinks regardless of relevance (Terraforming Mars ranked **#45/50** for
a query it should win). That is not a ranking; it is a data-entry accident leaking into search.

The embedder is fixed and query-agnostic. The two things actually under our control are the
**model** that produces the vector and the **text** fed into it.

## Decision

Treat the **embedded text as the primary lever**. Run every game through an enrichment pipeline
(`app/ingestion/enricher/`: curator → web → synth → compose) that turns uneven input into uniform,
dense, factual, search-friendly records *before* embedding — adding signal, never inventing — so
the retriever ranks the games, not their data entry. Structured "certain data" bypasses the LLM and
**always wins** (`curator.py`); the LLM only fills and rewrites around it.

## Alternatives considered

- **Swap in a stronger / larger embedding model.** Rejected as the *first* move: it raises the
  floor for everyone but does not close the gap between a three-paragraph game and a one-line one —
  a better model still embeds an empty record as empty. The text problem is upstream of the model.
- **Add a reranker on top.** A reranker reorders candidates that retrieval already surfaced; a game
  buried at #45 because its record is thin never enters the candidate window to be reranked.
- **Hand-clean the catalog.** Does not survive a real, growing, multi-source catalog; it proves a
  *tailored* example works, not that the mechanism does. (See the Italian-data rationale in the
  README: the messy real prose *is* the test.)

## Consequences

- **Win, measured:** same embedder, same query, only the text changes → Terraforming Mars
  **#45 → #1** on the frozen 50-game corpus. This is the whole project's thesis, made falsifiable.
- **Honest loss, kept visible:** on an already-rich record the Synth step *over-compresses* —
  Viticulture went **#4 → #23** (lost the *vino/toscana* signal). We did not hide it: it is written
  up in [`docs/enrichment/e2e-findings.md`](../enrichment/e2e-findings.md) and pinned by an `xfail`
  test that turns green only when fixed. A lever powerful enough to lift a game is powerful enough
  to drop one — recording both is the cost of believing the first number.
- The enrichment pipeline becomes a real subsystem to build, measure, and maintain (the bulk of
  `app/ingestion/`), and ingestion now depends on an LLM and the web step. Justified only because
  the lever is the one that actually moves the ranking.
- A future intentional boost layer (margin, promotions) must stay an **explicit** layer on top —
  never re-inherited from data quality, which is exactly what this decision removed.

## Revisited 2026-07-03 — the deferred alternative, measured

The alternative this ADR rejected *as the first move* was eventually made and measured
([SEL-107](../tickets/resolved/SEL-107-multilingual-embedder.md), ledger rows 1-2 in
[`docs/experiments.md`](../experiments.md)): swapping `nomic-embed-text` → `bge-m3` lifted
Recall@5 0.25 → 0.43 **on the raw, un-enriched text** — an aggregate gain roughly 9× what the
enrichment pipeline had bought (+0.02). The decision's core claim survives — a better model
still embeds an empty record as empty, and only enrichment *creates* signal where there is
none — but its implicit bet that the text was the *larger* lever did not: `nomic` was leaving
most of the already-present Italian signal unread. Both levers stay, because they fix different
failure modes: embedder = read the signal that exists; enrichment = create the signal that
doesn't; structured filters = the axes prose never carries (see SEL-142).
