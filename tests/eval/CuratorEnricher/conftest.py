"""Fixtures of the Curator eval (REAL LLM).

The LLM calls are SLOW (minutes for the 10 cases on CPU). Each run saves the whole report in
`runs/<timestamp>.json` + `runs/last.json` (gitignored) — offline analysis without re-running.

Scoring (slot-filling TP/FP/FN/TN → Precision/Recall/F-β) and run persistence live in
`report.CuratorReport` (shared mechanics in `tests/eval/report/eval_report.py`); this conftest
only wires the recording fixture and delegates the session hooks.

    docker exec seller-api python -m pytest tests/eval/CuratorEnricher -q
"""

from pathlib import Path

import pytest

from tests.eval.CuratorEnricher.report import CuratorReport


def pytest_sessionstart(session):
    # One report per suite, suite-namespaced: every eval conftest's hooks fire in a combined
    # `pytest tests/eval` session, so a shared attribute would mix the suites' records.
    session._curator_report = CuratorReport(Path(__file__).parent / "runs")


def pytest_sessionfinish(session, exitstatus):
    report = getattr(session, "_curator_report", None)
    if report is not None:
        report.finish(int(exitstatus))


@pytest.fixture
def record_assess(request):
    """Tests record one entry per case (slug, expect, llm_output, per_slot, counts, ...)."""
    return request.session._curator_report.record
