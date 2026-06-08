"""PHASE 3 — The embeddings are "good": common queries retrieve the game in the first screen.

Framing (see README, "Retrieval is a first screen"):
vector search is NOT meant to be a fine filter. On a large catalog (hundreds of games) its job is
the FIRST SCREEN: given a query as a user would type it, bring the right game into the candidate
set (top-K, K wide). Refining by setting, duration, etc. is a LATER, dynamic LLM step, with the
retrieved candidates in context — not the embedding's job. So here we measure RECALL in the
screen, not detail keywords.

Reads the metrics from the `scorecard` (computed once). Three things:
  - common queries retrieve the game in the screen (baseline embedding quality);
  - enrichment RECOVERS poor-DTO products (where the raw DTO leaves them out);
  - documented regression: on already-rich DTOs the Synth compresses too much and can WORSEN the
    screen → xfail (see docs/enrichment/e2e-findings.md), which is exactly what the e2e must expose.
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
    """The real value of enrichment: for poor-DTO products (strip_certain), where the raw DTO
    leaves the game OUT of the screen, the pipeline brings it back IN."""
    poor = [c for c in ingest.cases if c.strip_certain]
    assert poor, "no stripped-DTO case (strip_certain) to measure recovery"
    for c in poor:
        m = scorecard.games[c.slug]
        assert m.avg_rank_full < m.avg_rank_base, (
            f"{c.slug}: enrichment did not recover the poor DTO "
            f"(avg full={m.avg_rank_full} >= base={m.avg_rank_base})"
        )
        assert min(m.ranks_full) <= scorecard.screen_k, (
            f"{c.slug}: not even the best query enters the full screen (ranks={m.ranks_full})"
        )


@pytest.mark.xfail(
    reason="KNOWN REGRESSION (see docs/enrichment/e2e-findings.md): on already-rich DTOs the "
           "SynthEnricher compresses the description to ~700 chars and loses recall the baseline "
           "keeps — the vector would hold more text. To fix by calibrating the Synth budget. The "
           "test is written for the EXPECTED post-fix behavior; xfail until the Synth is improved.",
    strict=False,
)
def test_synth_does_not_degrade_rich_dto(ingest, scorecard):
    """EXPECTED (post-fix): on an already-rich DTO, enrichment must not worsen the screen vs the
    deterministic baseline. Fails today: it's the finding the e2e must expose."""
    rich = [c for c in ingest.cases if not c.strip_certain]
    assert rich, "no rich-DTO case to measure Synth (non-)regression"
    for c in rich:
        m = scorecard.games[c.slug]
        assert m.avg_rank_full <= m.avg_rank_base, (
            f"{c.slug}: the Synth worsens the screen on the rich DTO "
            f"(avg full={m.avg_rank_full} > base={m.avg_rank_base})"
        )
