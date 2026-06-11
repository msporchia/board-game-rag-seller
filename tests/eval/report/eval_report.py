"""EvalReport — the base class every eval suite's report extends.

An eval run works the same way in every suite: tests record one entry per case; at session end
the records are scored, persisted to `runs/<prefix>_<timestamp>.json` + `runs/last.json`
(gitignored), and printed with the delta vs the previous run — that history is how prompt and
model changes are judged (improved or regressed), so it is never skipped.

The base owns those shared mechanics. A subclass owns the SCORING and the human summary, as
overridable methods — changing how one suite ranks/scores its responses means overriding a
method in THAT suite's report class (`tests/eval/<Suite>/report.py`), never editing shared
machinery:

    class MyReport(EvalReport):
        prefix = "mystep"                     # runs/mystep_<timestamp>.json
        title = "MySuite — my_step()"         # summary header, left side
        measure = "what the numbers mean"     # summary header, right side

        def aggregate(self) -> dict: ...                          # records -> metrics
        def summary_lines(self, metrics, prev) -> list[str]: ...  # metrics -> printed lines

Conftests stay fixtures-only (per the test conventions): they construct the report at
`pytest_sessionstart`, expose `report.record` as the suite's recording fixture, and delegate
`pytest_sessionfinish` to `report.finish` — one line each.
"""

import json
import time
from pathlib import Path


class EvalReport:
    prefix = "eval"
    title = "eval"
    measure = ""
    model_label = "model"

    def __init__(self, runs_dir: Path):
        self.runs = runs_dir
        self.runs.mkdir(exist_ok=True)
        self.records: list[dict] = []
        self.started = time.strftime("%Y%m%d-%H%M%S")

    def record(self, entry: dict) -> None:
        self.records.append(entry)

    # ---- scoring: every suite defines its own ----------------------------------------

    def aggregate(self) -> dict:
        """Fold `self.records` into the metrics dict that is persisted and diffed across runs."""
        raise NotImplementedError

    def summary_lines(self, metrics: dict, prev: dict | None) -> list[str]:
        """The human summary printed between the header and the footer rules."""
        raise NotImplementedError

    # ---- shared mechanics --------------------------------------------------------------

    def model(self) -> str:
        """The model whose quality the numbers describe (subclasses may point elsewhere)."""
        try:
            from app.config import settings
            return settings.llm_model
        except Exception:                   # noqa: BLE001  settings unavailable → unknown
            return "unknown"

    def previous_metrics(self) -> dict | None:
        """Metrics of the most recent timestamped run file; `None` without history."""
        timestamped = sorted(p for p in self.runs.glob(f"{self.prefix}_*.json"))
        if not timestamped:
            return None
        try:
            prev = json.loads(timestamped[-1].read_text(encoding="utf-8"))
        except Exception:                   # noqa: BLE001  corrupted file → ignore
            return None
        return prev.get("metrics")

    def delta(self, curr: float, prev: float | None) -> str:
        if prev is None:
            return f"{curr:.3f}"
        d = curr - prev
        arrow = "→" if abs(d) < 1e-4 else ("↑" if d > 0 else "↓")
        return f"{curr:.3f} {arrow} (Δ {d:+.3f}, was: {prev:.3f})"

    def finish(self, exitstatus: int) -> None:
        if not self.records:
            return
        metrics = self.aggregate()
        prev = self.previous_metrics()
        payload = {
            "session": self.started,
            "model": self.model(),
            "exit_status": int(exitstatus),
            "metrics": metrics,
            "records": self.records,
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        (self.runs / f"{self.prefix}_{self.started}.json").write_text(text, encoding="utf-8")
        (self.runs / "last.json").write_text(text, encoding="utf-8")

        print("\n" + "=" * 70)
        print(f"  EVAL {self.title} | {self.model_label}: {payload['model']} | {self.measure}")
        print("=" * 70)
        for line in self.summary_lines(metrics, prev):
            print(line)
        print("=" * 70 + "\n")
