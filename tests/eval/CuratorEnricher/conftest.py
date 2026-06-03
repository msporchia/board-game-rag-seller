"""Persistence + scoring of the Curator eval (REAL LLM).

The LLM calls are SLOW (~2-5 min for the 10 cases). Each run saves the whole report in
`runs/<timestamp>.json` + `runs/last.json` (gitignored) — offline analysis without re-running.

At `pytest_sessionfinish` we compute the STANDARD slot-filling METRICS (TP/FP/FN/TN →
Precision/Recall/F-β) over the records collected by the tests, and we show the **diff vs the
previous run** (the most recent timestamped file in `runs/` EARLIER than the current run).
"""

import json
import time
from pathlib import Path

import pytest

RUNS = Path(__file__).parent / "runs"


def pytest_sessionstart(session):
    RUNS.mkdir(exist_ok=True)
    session._eval_records: list[dict] = []
    session._eval_started = time.strftime("%Y%m%d-%H%M%S")


@pytest.fixture
def record_assess(request):
    def _record(entry: dict) -> None:
        request.session._eval_records.append(entry)
    return _record


# ---- scoring helpers --------------------------------------------------------

def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def _f_beta(p: float, r: float, beta: float) -> float:
    """F-β = (1+β²)·P·R / (β²·P + R). β<1 favors precision, β>1 favors recall."""
    b2 = beta * beta
    return _safe_div((1 + b2) * p * r, b2 * p + r)


def _aggregate(records: list[dict]) -> dict:
    """Aggregates TP/FP/FN/TN over all records + computes P/R/F-β at the GLOBAL and per-slot level."""
    total = {"TP": 0, "FP": 0, "FN": 0, "TN": 0, "SKIP": 0}
    per_slot: dict[str, dict] = {}
    for rec in records:
        for k, v in rec.get("counts", {}).items():
            total[k] += v
        for slot, info in rec.get("per_slot", {}).items():
            slot_counts = per_slot.setdefault(slot, {"TP": 0, "FP": 0, "FN": 0, "TN": 0, "SKIP": 0})
            slot_counts[info["outcome"]] += 1

    p = _safe_div(total["TP"], total["TP"] + total["FP"])
    r = _safe_div(total["TP"], total["TP"] + total["FN"])
    return {
        "counts": total,
        "precision": round(p, 4),
        "recall": round(r, 4),
        "f1": round(_f_beta(p, r, 1.0), 4),
        "f0_5": round(_f_beta(p, r, 0.5), 4),     # precision weighs 4× more than recall
        "f0_25": round(_f_beta(p, r, 0.25), 4),   # precision weighs 16× more than recall
        "per_slot": per_slot,
    }


def _previous_metrics() -> dict | None:
    """Metrics of the PREVIOUS run (the most recent timestamped file in `runs/`, ignoring
    `last.json`). `None` if there's no history."""
    timestamped = sorted(p for p in RUNS.glob("assess_*.json"))
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
    print(f"  EVAL Curator — assess() | model: {model} | slot-filling scoring")
    print("=" * 70)
    c = metrics["counts"]
    n_eval = c["TP"] + c["FP"] + c["FN"] + c["TN"]
    print(f"  Slots evaluated: {n_eval} (skip structurally-present: {c['SKIP']})")
    print(f"  TP={c['TP']}  FP={c['FP']}  FN={c['FN']}  TN={c['TN']}")
    print()
    pm = (prev or {}).get if prev else lambda _k: None
    for label, key in (("Precision", "precision"), ("Recall", "recall"),
                       ("F1       ", "f1"), ("F0.5     ", "f0_5"),
                       ("F0.25    ", "f0_25")):
        print(f"  {label}: {_format_delta(metrics[key], pm(key) if prev else None)}")
    print()
    print(f"  {'slot':28s}  {'TP':>3s} {'FP':>3s} {'FN':>3s} {'TN':>3s}")
    for slot, sc in metrics["per_slot"].items():
        print(f"  {slot:28s}  {sc['TP']:>3d} {sc['FP']:>3d} {sc['FN']:>3d} {sc['TN']:>3d}")
    print("=" * 70 + "\n")


def pytest_sessionfinish(session, exitstatus):
    records = getattr(session, "_eval_records", None)
    if not records:
        return
    timestamp = session._eval_started
    metrics = _aggregate(records)
    prev_metrics = _previous_metrics()

    payload = {
        "session": timestamp,
        "model": _peek_model(),
        "exit_status": int(exitstatus),
        "n_cases": len(records),
        "metrics": metrics,
        "records": records,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (RUNS / f"assess_{timestamp}.json").write_text(text, encoding="utf-8")
    (RUNS / "last.json").write_text(text, encoding="utf-8")

    _print_summary(metrics, prev_metrics, payload["model"])


def _peek_model() -> str:
    try:
        from app.config import settings
        return settings.llm_model
    except Exception:                       # noqa: BLE001  settings unavailable → unknown
        return "unknown"
