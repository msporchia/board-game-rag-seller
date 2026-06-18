"""Fixtures of the TurnAnalyzer eval (REAL LLM).

The analyze step is ONE structured LLM call that reads the customer along independent
dimensions (enthusiasm, decisiveness, expertise_level, reply_style + the escalation contract).
Each dimension is evaluated SEPARATELY: every fixture conversation is crafted to emphasize one
dimension and carries an oracle label only for it — so each aspect fails alone and is weighed
alone, never averaged into an end-to-end blob.

Scoring and run persistence live in `report.TurnAnalyzerReport` (shared mechanics in
`tests/eval/report/eval_report.py`); this conftest only wires fixtures and delegates the
session hooks.

The analyzer under eval is built EXACTLY like production (`ChatGraph.__init__`): same model,
same temperature 0, same structured-output schema, same prompt (`ChatGraph._analysis_prompt`)
— minus the trace callbacks, so eval runs don't pollute the production `traces` table.

    docker exec seller-api python -m pytest tests/eval/TurnAnalyzer -q
"""

from pathlib import Path

import pytest

from tests.eval.TurnAnalyzer.report import TurnAnalyzerReport


def pytest_sessionstart(session):
    # One report per suite, suite-namespaced: every eval conftest's hooks fire in a combined
    # `pytest tests/eval` session, so a shared attribute would mix the suites' records.
    session._turn_analyzer_report = TurnAnalyzerReport(Path(__file__).parent / "runs")


def pytest_sessionfinish(session, exitstatus):
    report = getattr(session, "_turn_analyzer_report", None)
    if report is not None:
        report.finish(int(exitstatus))


@pytest.fixture
def record_analysis(request):
    """Tests record one entry per case:
    {case, dimension, expected, got, ok, note, ...extra fields kept in the report}."""
    return request.session._turn_analyzer_report.record


@pytest.fixture(scope="session")
def analyzer():
    """The production-shaped analyze call: (history, message) -> TurnAnalysis."""
    from langchain_ollama import ChatOllama

    from app.chat.analyzer import TurnAnalyzer
    from app.chat.models.analysis import TurnAnalysis
    from app.config import settings

    llm = ChatOllama(
        model=settings.llm_model, base_url=settings.ollama_url, temperature=0.0,
    ).with_structured_output(TurnAnalysis)

    def _analyze(history: list[str], message: str) -> "TurnAnalysis":
        return llm.invoke(TurnAnalyzer.prompt(history, message))

    return _analyze
