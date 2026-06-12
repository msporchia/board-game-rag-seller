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

    def sections(self) -> dict:
        """How the records are laid out in the persisted run file.

        The file is a READING surface, not a log: subclasses regroup the records so that
        failures come first, grouped the way the suite is read (per dimension, per strategy),
        each failure self-contained — everything needed to judge the case without opening
        fixtures or rerunning. Default: the raw records, for suites without a better shape.
        """
        return {"records": self.records}

    def headline(self, metrics: dict) -> str:
        """One markdown line with the suite's number that matters (for RESULTS.md and the
        index table): e.g. 'micro-accuracy **0.870** · 54 cases'."""
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
            **self.sections(),
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

        self._write_markdown(metrics, prev, payload["model"])

    # ---- versioned markdown (the showcase surface: RESULTS.md + the suite index) ----------

    def _write_markdown(self, metrics: dict, prev: dict | None, model: str) -> None:
        """Regenerate `<suite>/RESULTS.md` (committed, unlike runs/) and the cross-suite
        index `tests/eval/RESULTS.md`: a visitor must see how many cases ran and where the
        model fails without digging into gitignored run files."""
        suite_dir = self.runs.parent
        lines = [
            "<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->",
            f"# Eval — {self.title}",
            "",
            f"> {self.headline(metrics)} · {self.model_label} `{model}` "
            f"· session {self.started}",
            "",
            "```",
            *self.summary_lines(metrics, prev),
            "```",
            "",
            *self._markdown_failures(),
            *self._markdown_passes(),
            "The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); "
            "the machine-readable history stays in `runs/` (local, gitignored).",
            "",
        ]
        (suite_dir / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
        self._write_index(suite_dir.parent)

    def _markdown_failures(self) -> list[str]:
        failures = self.sections().get("failures") or {}
        grouped = failures if isinstance(failures, dict) else {None: failures}
        entries = [(g, e) for g, lst in grouped.items() for e in lst]
        if not entries:
            return ["## Failures", "", "None in this run.", ""]

        lines = [f"## Failures ({len(entries)})", ""]
        for group, entry in entries:
            prefix = f"{group} — " if group else ""
            lines.append(f"### {prefix}{entry.get('case', '?')}")
            for key, val in entry.items():
                if key == "case" or val in (None, "", [], {}):
                    continue
                if isinstance(val, list):
                    lines.append(f"- {key}:")
                    lines += [f"  - {self._md_value(v)}" for v in val]
                else:
                    lines.append(f"- {key}: {self._md_value(val)}")
            lines.append("")
        return lines

    def _markdown_passes(self) -> list[str]:
        """Successes below the failures, one compact entry each: less relevant than the
        failures, but they show what the good cases look like without drowning the page.
        String entries render as one line; dict entries as one line of scalar fields plus
        nested lines for list-valued fields (e.g. a compact trajectory)."""
        passes = self.sections().get("passes") or {}
        grouped = passes if isinstance(passes, dict) else {None: passes}
        entries = [(g, e) for g, lst in grouped.items() for e in lst]
        if not entries:
            return []
        lines = [f"## Passes ({len(entries)})", ""]
        for group, entry in entries:
            prefix = f"{group} — " if group else ""
            if not isinstance(entry, dict):
                lines.append(f"- {prefix}{entry}")
                continue
            scalars = [f"{k} {v}" for k, v in entry.items()
                       if k != "case" and not isinstance(v, list) and v not in (None, "")]
            lines.append(f"- {prefix}**{entry.get('case', '?')}**"
                         + (f" — {', '.join(scalars)}" if scalars else ""))
            for val in (v for v in entry.values() if isinstance(v, list)):
                lines += [f"  - {self._md_value(v)}" for v in val]
        lines.append("")
        return lines

    @staticmethod
    def _md_value(val) -> str:
        if isinstance(val, dict):
            return ", ".join(f"{k}={v!r}" for k, v in val.items())
        return f"`{val}`" if isinstance(val, (int, float, bool)) else str(val)

    def _write_index(self, eval_root: Path) -> None:
        """Rebuild the suite index from every sibling RESULTS.md headline blockquote."""
        rows = []
        for results in sorted(eval_root.glob("*/RESULTS.md")):
            head = next((ln[2:] for ln in results.read_text(encoding="utf-8").splitlines()
                         if ln.startswith("> ")), None)
            if head:
                rows.append(f"| {results.parent.name} | {head} | "
                            f"[{results.parent.name}/RESULTS.md]({results.parent.name}/RESULTS.md) |")
        lines = [
            "<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->",
            "# Eval results — last runs",
            "",
            "One line per suite, regenerated whenever that suite runs. Each page lists the",
            "per-case failures (the interesting part) and links the oracle fixtures.",
            "",
            "| suite | last run | details |",
            "|---|---|---|",
            *rows,
            "",
        ]
        (eval_root / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
