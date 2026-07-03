# Enrichment — e2e findings

What running the real pipeline end to end surfaced (not opinion: measured by the actual retriever,
on a Qdrant collection of ~50 games with the oracle queries). Produced and gated by
`tests/e2e/enrichment` (see its README). Update when these change.

## 1. The Synth compresses too much and loses recall on rich DTOs  ⚠️ open

**Observation.** On a game with an already-rich product sheet (e.g. Viticulture), the full
pipeline places the game **worse** than the deterministic baseline (`rule`, compose only) on some
common queries:

| query | full | base |
|---|---|---|
| Viticulture — "vendemmia/stagioni/vigna" | #23 | #4 |
| Viticulture — "tenuta vinicola in Toscana" | #3 | #1 |

**Measurement, not judgement.** "Worse" = the actual position returned by the `GameRetriever` on
the same queries with the same 47 distractors, in two collections identical except the target
game's text (`e2e_enrichment_full` vs `e2e_enrichment_base`). The baseline is the DTO **as-is**
through the deterministic compose only (= the `rule` pipeline, the official baseline-to-beat in
`tests/eval_suite.py`), indexed and queried by the vector.

**Cause.** The `SynthEnricher` rewrites `enriched.description` with a `~700 char` cap
(`synth.py:_MAX_CHARS`). On rich-sheet games, the full embed_text is ≈1200 chars vs ≈2300 for the
baseline: the Synth **compresses** instead of "rewriting without compressing" (the very risk noted
in `03-synth.md`). Keyword count (substring, so the *why hypothesis*, not the vector's verdict):
Viticulture full loses `vino`/`toscana`; Terraforming Mars full loses `ossigeno`/`temperatura`/
`oceani`.

**How bad it really is.** Weigh it against the "first screen" philosophy (see the e2e README):
many of those keywords (oceans, oxygen) are not realistic user queries, so losing them matters
less than it looks — an LLM re-reads them after fetching the candidates. But it is still true that
the compression makes the game **slip out of the screen** even on common queries → to fix.

**Proposal.** Raise/calibrate the Synth budget to the embedder's real capacity: if
`nomic-embed-text` comfortably holds ~N words, synthesizing to a fraction (e.g. 200) **wastes
space**. Directions: (a) raise `_MAX_CHARS` toward the vector's useful capacity; (b) never let the
Synth drop below the baseline signal (preserve the material's thematic keywords, "rewrite not
compress"); (c) measure the embedder's useful capacity and derive the budget from it instead of a
fixed number.

**Test status.** `test_phase3_retrieval::test_synth_does_not_degrade_rich_dto` is written for the
expected post-fix behavior and marked `xfail` (red today) → it turns green when the Synth is
improved. It's the finding that justifies the e2e's existence.

## 2. Enrichment recovers poor-sheet products  ✅ confirmed

Conversely: on a stripped DTO (Terraforming Mars with no description) the baseline is nearly
invisible (#45 / #47 / #47), the full pipeline brings it back into the first screen (#1 / #26 / #1)
thanks to facts recovered from the Web. This is the real value of enrichment in production, where
many products have thin sheets. Verified by `test_enrichment_recovers_poor_dto`.

## 3. The Web fires selectively — and that's correct  ✅ confirmed

The WebEnricher fires only when the Curator leaves gaps (`missing_info`): stripped DTOs fire,
rich-sheet Viticulture does **not**. Intended behavior ("online only once local sources are
exhausted"), verified by `test_web_fires_only_when_expected`.
