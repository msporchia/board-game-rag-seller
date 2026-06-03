"""WebEnricher — RANKING phase EVAL (deterministic, no Ollama).

PURPOSE
-------
Before querying the LLM the step must put the RIGHT sources on top: whitelist first, blocklist
out, unknown ones at the tail. The ranking decides who ever sees the LLM — if we get this wrong,
the rest of the pipeline works on the wrong pages.

WHAT IT TESTS
-------------
For each fixture in `fixtures/*.json`, over REAL `search_results` (recorded from DDG):
- `top_domains` (if filled in the oracle): the first N ranked domains are EXACTLY the expected
  ones, IN THE SAME ORDER. Asserted only on the prefix of length `len(top_domains)` — the rest
  is free.
- `must_drop_domains`: none of these domains appear in the ranked results (e.g. our own shop,
  known retailers — they must be dropped by the blocklist).

HOW
---
No LLM, no network: only `WebEnricher._ranked` over the results frozen in the fixture.
NON-llm marker (runs even without Ollama).

    docker exec seller-api python -m pytest tests/eval/WebEnricher/test_ranking.py -q
"""

import pytest

from tests.eval.WebEnricher.replay import all_fixtures, load_fixture, ranked_results

FIXTURES = all_fixtures()


@pytest.mark.skipif(not FIXTURES, reason="no fixture recorded: run tests.eval.WebEnricher.recorder")
@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
class TestWebEnricherRanking:
    """Deterministic source ranking over real search_results, per game."""

    def test_top_domains_match_expected_prefix(self, path):
        """The first N ranked domains match `expect.ranking.top_domains` (in order)."""
        fix = load_fixture(path)
        expected = fix.get("expect", {}).get("ranking", {}).get("top_domains", []) or []
        if not expected:
            pytest.skip("`top_domains` oracle not filled for this fixture")
        actual = [r.domain for r in ranked_results(fix)][:len(expected)]
        assert actual == expected, (
            f"[{fix['name']}] different ranking prefix\n  expected: {expected}\n  now:      {actual}"
        )

    def test_must_drop_domains_absent(self, path):
        """The domains in `must_drop_domains` don't appear in the ranked results (effective blocklist)."""
        fix = load_fixture(path)
        must_drop = set(fix.get("expect", {}).get("ranking", {}).get("must_drop_domains", []) or [])
        if not must_drop:
            pytest.skip("`must_drop_domains` oracle not filled for this fixture")
        domains = {r.domain for r in ranked_results(fix)}
        leaked = domains & must_drop
        assert not leaked, f"[{fix['name']}] domains that should have been dropped but passed: {sorted(leaked)}"
