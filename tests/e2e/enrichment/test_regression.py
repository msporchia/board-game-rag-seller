"""REGRESSION GATE — compares the run's scorecard against the git-versioned baseline.

This is the requested "improved/regressed" signal: no gate metric may regress beyond tolerance
versus `baseline.json` (see scorecard.py for metrics and tolerances). When an intended improvement
lands, regenerate the baseline with `python -m tests.e2e.enrichment run --update-baseline` and
commit it — git history becomes the quality trend.
"""

import pytest

from tests.e2e.enrichment.scorecard.baseline import Baseline

pytestmark = pytest.mark.e2e


def test_no_regression_vs_baseline(scorecard):
    baseline = Baseline.load()
    if baseline is None:
        pytest.skip("no baseline.json: create it with `run --update-baseline` and commit it")

    comparison = baseline.compare(scorecard)
    print("\n" + comparison.table())
    assert not comparison.has_gating_regression, (
        "regression beyond tolerance vs baseline:\n  "
        + "\n  ".join(f"{r.game}.{r.metric}: {r.baseline} -> {r.current}"
                      for r in comparison.regressions())
    )
