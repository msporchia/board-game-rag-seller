"""PHASE 3 — The embeddings are "good": common queries retrieve the game in the first screen.

Framing (see README, "Retrieval is a first screen"):
vector search is NOT meant to be a fine filter. On a large catalog (hundreds of games) its job is
the FIRST SCREEN: given a query as a user would type it, bring the right game into the candidate
set (top-K, K wide). Refining by setting, duration, etc. is a LATER, dynamic LLM step, with the
retrieved candidates in context — not the embedding's job. So here we measure RECALL in the
screen, not detail keywords.

Reads the metrics from the `scorecard` (computed once). Three things:
  - common queries retrieve the game in the screen (baseline embedding quality);
  - enrichment on poor DTOs: recovery-or-no-harm (recovery when the base is out of the screen;
    never pushing it out when a strong embedder already keeps it in — ledger rows 4-6);
  - the once-xfailed Viticulture regression (rich DTO worsened by the old synth) is now a plain
    green guard: erased by SEL-144 + bge-m3, it must never come back (e2e-findings.md).
"""

import pytest

pytestmark = pytest.mark.e2e


def test_canonical_query_in_first_screen(ingest, scorecard):
    """The canonical query (the most common, oracle[0]) brings the game into the first screen."""
    k = scorecard.screen_k
    for c in ingest.cases:
        r0 = scorecard.games[c.slug].ranks_full[0]
        assert r0 <= k, (
            f"{c.slug}: canonical query out of the screen (#{r0}>{k}): {c.must_find_queries[0]!r}"
        )


def test_most_common_queries_in_first_screen(scorecard):
    """Most common queries retrieve the game in the screen (robust recall)."""
    for slug, m in scorecard.games.items():
        assert m.queries_in_screen_full >= 2, (
            f"{slug}: only {m.queries_in_screen_full}/{m.n_queries} queries in the top-"
            f"{scorecard.screen_k} screen (full ranks={m.ranks_full})"
        )


def test_enrichment_recovers_poor_dto(ingest, scorecard):
    """The real value of enrichment on poor DTOs (strip_certain), stated so it survives
    embedder eras: if the raw DTO leaves the game OUT of the screen, the pipeline must bring
    it IN; if a strong embedder already reads the name/tags well enough to keep it IN (the
    bge-m3 era reality for name-informative games — ledger rows 4-6), enrichment must NOT
    push it out. The nomic-era strict `full < base` is impossible against a base already at
    rank ~1 — the contract is recovery-or-no-harm, not beating perfection."""
    poor = [c for c in ingest.cases if c.strip_certain]
    assert poor, "no stripped-DTO case (strip_certain) to measure recovery"
    for c in poor:
        m = scorecard.games[c.slug]
        base_in_screen = m.avg_rank_base <= scorecard.screen_k
        if not base_in_screen:
            assert m.avg_rank_full < m.avg_rank_base, (
                f"{c.slug}: enrichment did not recover the poor DTO "
                f"(avg full={m.avg_rank_full} >= base={m.avg_rank_base})"
            )
        assert m.avg_rank_full <= scorecard.screen_k, (
            f"{c.slug}: enrichment left/pushed the game out of the top-{scorecard.screen_k} "
            f"screen (avg full={m.avg_rank_full}, base={m.avg_rank_base})"
        )
        assert min(m.ranks_full) <= scorecard.screen_k, (
            f"{c.slug}: not even the best query enters the full screen (ranks={m.ranks_full})"
        )


def test_synth_does_not_degrade_rich_dto(ingest, scorecard):
    """On an already-rich DTO, enrichment must not worsen the screen vs the deterministic
    baseline. HISTORY: born as an xfail pinning the Viticulture regression (the nomic-era
    synth compressed rich records to ~700 chars and lost recall — docs/enrichment/
    e2e-findings.md, docs/showcase/viticulture.md). The SEL-144 recalibration (budget 1600,
    concept-checklist prompt) plus the bge-m3 embedder erased it — measured, ledger rows 6/9 —
    so the pin is now a plain green guard: if the regression ever returns, this goes red."""
    rich = [c for c in ingest.cases if not c.strip_certain]
    assert rich, "no rich-DTO case to measure Synth (non-)regression"
    for c in rich:
        m = scorecard.games[c.slug]
        assert m.avg_rank_full <= m.avg_rank_base, (
            f"{c.slug}: the Synth worsens the screen on the rich DTO "
            f"(avg full={m.avg_rank_full} > base={m.avg_rank_base})"
        )
