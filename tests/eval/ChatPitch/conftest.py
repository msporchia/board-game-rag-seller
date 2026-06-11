"""Fixtures of the ChatPitch eval (REAL LLM).

ChatPitch measures the GENERATE step alone (`ChatAdvisor.pitch`): known hits in, structured
reply out — no retrieval, no graph. It exists to turn the open finding of docs/chat.md into a
number: in the live smoke, llama3.1-8B produced zero valid recommendations and the
deterministic fallback fired every time.

Scoring and run persistence live in `report.PitchReport` (shared mechanics in
`tests/eval/report/eval_report.py`); this conftest only wires fixtures and delegates the
session hooks. The fallback-detection method and the behavioral checks are defined and
documented in `test_pitch.py`.

The LLM under eval is built EXACTLY like ChatAdvisor's default (same model, same temperature
0.4, same structured-output schema) — minus the trace callbacks, so eval runs don't pollute
the production `traces` table. It is handed to pitch() per call via the `llm` override, the
same hook production uses for model tiering.

    docker exec seller-api python -m pytest tests/eval/ChatPitch -q
"""

from pathlib import Path

import pytest

from tests.eval.ChatPitch.report import PitchReport


def pytest_sessionstart(session):
    # One report per suite, suite-namespaced: every eval conftest's hooks fire in a combined
    # `pytest tests/eval` session, so a shared attribute would mix the suites' records.
    session._chat_pitch_report = PitchReport(Path(__file__).parent / "runs")


def pytest_sessionfinish(session, exitstatus):
    report = getattr(session, "_chat_pitch_report", None)
    if report is not None:
        report.finish(int(exitstatus))


@pytest.fixture
def record_pitch(request):
    """Tests record one entry per case:
    {case, strategy, expertise_level, fallback, within_k, asks_question, proposes_enough,
     jargon_free, ...extra fields kept in the report}. The behavioral booleans are None
    when out of scope (wrong strategy/expertise, or fallback fired)."""
    return request.session._chat_pitch_report.record


@pytest.fixture(scope="session")
def advisor():
    """A ChatAdvisor whose collaborators are the unit fakes: pitch() never touches the
    retriever, and the constructor-level fake LLM is never invoked because every call goes
    through the `llm` override (it raises on invoke, so an accidental use would be loud)."""
    from app.chat.advisor import ChatAdvisor
    from tests.unit.ChatAdvisor.fakes import FakeRetriever, FakeStructuredLLM

    return ChatAdvisor(retriever=FakeRetriever([]), llm=FakeStructuredLLM(raises=True))


@pytest.fixture(scope="session")
def pitch_llm():
    """ChatAdvisor's default generation model (same model, same temperature 0.4, same
    ChatReply schema — see `ChatAdvisor.__init__`), rebuilt WITHOUT trace callbacks so eval
    runs don't write to the production `traces` table."""
    from langchain_ollama import ChatOllama

    from app.chat.models.reply import ChatReply
    from app.config import settings

    return ChatOllama(
        model=settings.llm_model, base_url=settings.ollama_url, temperature=0.4,
    ).with_structured_output(ChatReply)
