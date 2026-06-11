"""Persistence + scoring of the ChatPitch eval (REAL LLM).

ChatPitch measures the GENERATE step alone (`ChatAdvisor.pitch`): known hits in, structured
reply out — no retrieval, no graph. It exists to turn the open finding of docs/chat.md into a
number: in the live smoke, llama3.1-8B produced zero valid recommendations and the
deterministic fallback fired every time. This suite measures that rate over curated cases.

Headline metric: **fallback_rate** — the share of cases where pitch() degraded to the
deterministic reply (structured-output failure, or no recommendation id surviving grounding
validation). The behavioral rates are computed on the NON-fallback replies only, because on a
fallback the text comes from deterministic code, not from the model:
  - games_within_k        — recommended games respect STRATEGY_K of the turn's strategy.
  - guided_asks_question  — GUIDED replies close with a question (the strategy contract).
  - quick_match_proposes  — QUICK_MATCH replies propose >= 3 games when >= 3 hits are given.
  - beginner_jargon_free  — beginner replies avoid a small fixed jargon lexicon (blunt
    substring check, defined and documented in test_pitch.py).

Like the sibling suites (CuratorEnricher, TurnAnalyzer) there is NO acceptance threshold: the
first runs establish the baseline, the diff vs the previous run flags regressions
(`runs/<timestamp>.json` + `runs/last.json`, gitignored).

The LLM under eval is built EXACTLY like ChatAdvisor's default (same model, same temperature
0.4, same structured-output schema) — minus the trace callbacks, so eval runs don't pollute
the production `traces` table. It is handed to pitch() per call via the `llm` override, the
same hook production uses for model tiering.

    docker exec seller-api python -m pytest tests/eval/ChatPitch -q
"""

import json
import time
from pathlib import Path

import pytest

RUNS = Path(__file__).parent / "runs"


def pytest_sessionstart(session):
    RUNS.mkdir(exist_ok=True)
    # Suite-namespaced (not `_eval_records`): every eval conftest's hooks fire in a combined
    # `pytest tests/eval` session, so a shared attribute would mix the suites' records.
    session._chat_pitch_records: list[dict] = []
    session._chat_pitch_started = time.strftime("%Y%m%d-%H%M%S")


@pytest.fixture
def record_pitch(request):
    """Tests record one entry per case:
    {case, strategy, expertise_level, fallback, within_k, asks_question, proposes_enough,
     jargon_free, ...extra fields kept in the report}. The behavioral booleans are None
    when out of scope (wrong strategy/expertise, or fallback fired)."""
    def _record(entry: dict) -> None:
        request.session._chat_pitch_records.append(entry)
    return _record


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


# ---- scoring ----------------------------------------------------------------

# (metric name, record key, scope shown in the summary)
_RATE_KEYS = (
    ("fallback_rate", "fallback", "all cases — lower is better"),
    ("games_within_k", "within_k", "non-fallback replies"),
    ("guided_asks_question", "asks_question", "non-fallback GUIDED"),
    ("quick_match_proposes", "proposes_enough", "non-fallback QUICK_MATCH, >=3 hits"),
    ("beginner_jargon_free", "jargon_free", "non-fallback beginner"),
)


def _rate(records: list[dict], key: str) -> dict:
    """{n, ok, rate} over the records where `key` is in scope (not None)."""
    vals = [r[key] for r in records if r.get(key) is not None]
    ok = sum(1 for v in vals if v)
    return {"n": len(vals), "ok": ok, "rate": round(ok / len(vals), 4) if vals else None}


def _aggregate(records: list[dict]) -> dict:
    metrics: dict = {"n_cases": len(records)}
    for name, key, _scope in _RATE_KEYS:
        metrics[name] = _rate(records, key)
    metrics["fallback_cases"] = [r["case"] for r in records if r["fallback"]]
    return metrics


def _previous_metrics() -> dict | None:
    """Metrics of the PREVIOUS run (the most recent timestamped file in `runs/`, ignoring
    `last.json`). `None` if there's no history."""
    timestamped = sorted(p for p in RUNS.glob("pitch_*.json"))
    if not timestamped:
        return None
    try:
        prev = json.loads(timestamped[-1].read_text(encoding="utf-8"))
    except Exception:                       # noqa: BLE001  corrupted file → ignore
        return None
    return prev.get("metrics")


def _format_delta(curr: float, prev: float | None) -> str:
    if prev is None:
        return f"{curr:.3f}"
    d = curr - prev
    arrow = "→" if abs(d) < 1e-4 else ("↑" if d > 0 else "↓")
    return f"{curr:.3f} {arrow} (Δ {d:+.3f}, was: {prev:.3f})"


def _print_summary(metrics: dict, prev: dict | None, model: str) -> None:
    print("\n" + "=" * 70)
    print(f"  EVAL ChatPitch — pitch() | model: {model} | grounded-generation rates")
    print("=" * 70)
    print(f"  Cases: {metrics['n_cases']}")
    print()
    for name, _key, scope in _RATE_KEYS:
        m = metrics[name]
        prev_rate = (prev or {}).get(name, {}).get("rate")
        if m["rate"] is None:
            print(f"  {name:22s}    —     (no cases in scope: {scope})")
            continue
        print(f"  {name:22s} {m['ok']:>2d}/{m['n']:<2d} "
              f"{_format_delta(m['rate'], prev_rate)}   [{scope}]")
    if metrics["fallback_cases"]:
        print()
        print(f"  fallback fired on: {', '.join(metrics['fallback_cases'])}")
    print("=" * 70 + "\n")


def pytest_sessionfinish(session, exitstatus):
    records = getattr(session, "_chat_pitch_records", None)
    if not records:
        return
    timestamp = session._chat_pitch_started
    metrics = _aggregate(records)
    prev_metrics = _previous_metrics()

    payload = {
        "session": timestamp,
        "model": _peek_model(),
        "exit_status": int(exitstatus),
        "metrics": metrics,
        "records": records,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (RUNS / f"pitch_{timestamp}.json").write_text(text, encoding="utf-8")
    (RUNS / "last.json").write_text(text, encoding="utf-8")

    _print_summary(metrics, prev_metrics, payload["model"])


def _peek_model() -> str:
    try:
        from app.config import settings
        return settings.llm_model
    except Exception:                       # noqa: BLE001  settings unavailable → unknown
        return "unknown"
