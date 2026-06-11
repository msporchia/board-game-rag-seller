"""Persistence + scoring of the TurnAnalyzer eval (REAL LLM).

The analyze step is ONE structured LLM call that reads the customer along independent
dimensions (enthusiasm, decisiveness, expertise_level, reply_style + the escalation contract).
Each dimension is evaluated SEPARATELY: every fixture conversation is crafted to emphasize one
dimension and carries an oracle label only for it — so each aspect fails alone and is weighed
alone, never averaged into an end-to-end blob.

Scoring is per-dimension ACCURACY plus a confusion matrix (expected→got): for a salesperson,
mistaking `beginner` for `intermediate` is venial, `beginner` for `advanced` is a lost customer
— the confusion matrix is where that difference shows. Like the Curator eval, there is no
acceptance threshold yet: the first runs establish the baseline, the diff vs the previous run
flags regressions (`runs/<timestamp>.json` + `runs/last.json`, gitignored).

The analyzer under eval is built EXACTLY like production (`ChatGraph.__init__`): same model,
same temperature 0, same structured-output schema, same prompt (`ChatGraph._analysis_prompt`)
— minus the trace callbacks, so eval runs don't pollute the production `traces` table.

    docker exec seller-api python -m pytest tests/eval/TurnAnalyzer -q
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
    session._turn_analyzer_records: list[dict] = []
    session._turn_analyzer_started = time.strftime("%Y%m%d-%H%M%S")


@pytest.fixture
def record_analysis(request):
    """Tests record one entry per case:
    {case, dimension, expected, got, ok, note, ...extra fields kept in the report}."""
    def _record(entry: dict) -> None:
        request.session._turn_analyzer_records.append(entry)
    return _record


@pytest.fixture(scope="session")
def analyzer():
    """The production-shaped analyze call: (history, message) -> TurnAnalysis."""
    from langchain_ollama import ChatOllama

    from app.chat.graph import ChatGraph
    from app.chat.models.analysis import TurnAnalysis
    from app.config import settings

    llm = ChatOllama(
        model=settings.llm_model, base_url=settings.ollama_url, temperature=0.0,
    ).with_structured_output(TurnAnalysis)

    def _analyze(history: list[str], message: str) -> "TurnAnalysis":
        return llm.invoke(ChatGraph._analysis_prompt(history, message))

    return _analyze


# ---- scoring ----------------------------------------------------------------

def _aggregate(records: list[dict]) -> dict:
    """Per-dimension accuracy + confusion matrix, plus the global micro-accuracy."""
    per_dim: dict[str, dict] = {}
    for rec in records:
        dim = per_dim.setdefault(rec["dimension"], {"n": 0, "correct": 0, "confusion": {}})
        dim["n"] += 1
        dim["correct"] += int(rec["ok"])
        if not rec["ok"]:
            key = f"{rec['expected']} -> {rec['got']}"
            dim["confusion"][key] = dim["confusion"].get(key, 0) + 1
    for dim in per_dim.values():
        dim["accuracy"] = round(dim["correct"] / dim["n"], 4) if dim["n"] else 0.0

    n = len(records)
    correct = sum(int(r["ok"]) for r in records)
    return {
        "n_cases": n,
        "accuracy": round(correct / n, 4) if n else 0.0,
        "per_dimension": per_dim,
    }


def _previous_metrics() -> dict | None:
    timestamped = sorted(p for p in RUNS.glob("analyze_*.json"))
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
    prev_dims = (prev or {}).get("per_dimension", {})
    print("\n" + "=" * 70)
    print(f"  EVAL TurnAnalyzer — analyze | model: {model} | per-dimension accuracy")
    print("=" * 70)
    print(f"  Cases: {metrics['n_cases']}   "
          f"micro-accuracy: {_format_delta(metrics['accuracy'], (prev or {}).get('accuracy'))}")
    print()
    for name, dim in sorted(metrics["per_dimension"].items()):
        prev_acc = prev_dims.get(name, {}).get("accuracy")
        print(f"  {name:18s} {dim['correct']:>2d}/{dim['n']:<2d}  "
              f"{_format_delta(dim['accuracy'], prev_acc)}")
        for miss, count in sorted(dim["confusion"].items(), key=lambda kv: -kv[1]):
            print(f"  {'':18s}   ✗ {miss}  ×{count}")
    print("=" * 70 + "\n")


def pytest_sessionfinish(session, exitstatus):
    records = getattr(session, "_turn_analyzer_records", None)
    if not records:
        return
    timestamp = session._turn_analyzer_started
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
    (RUNS / f"analyze_{timestamp}.json").write_text(text, encoding="utf-8")
    (RUNS / "last.json").write_text(text, encoding="utf-8")

    _print_summary(metrics, prev_metrics, payload["model"])


def _peek_model() -> str:
    try:
        from app.config import settings
        return settings.llm_model
    except Exception:                       # noqa: BLE001  settings unavailable → unknown
        return "unknown"
