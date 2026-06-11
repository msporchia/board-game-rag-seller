"""TurnAnalyzerReport — scoring of the analyze eval (see eval_report.EvalReport)."""

from tests.eval.report.eval_report import EvalReport


class TurnAnalyzerReport(EvalReport):
    """Per-dimension accuracy, plus every miss as a readable per-case line.

    Every record carries the ONE dimension its case emphasizes, so dimensions never blur.
    The summary lists each miss as `case-id: expected -> got` — prompt tuning works one case
    at a time, so the failures must be openable one at a time (full record, including the
    oracle note, in `runs/last.json`). Severity is also a per-case judgement: mistaking
    `beginner` for `intermediate` is venial, `beginner` for `advanced` is a lost customer.
    """

    prefix = "analyze"
    title = "TurnAnalyzer — analyze"
    measure = "per-dimension accuracy"

    def aggregate(self) -> dict:
        per_dim: dict[str, dict] = {}
        for rec in self.records:
            dim = per_dim.setdefault(rec["dimension"], {"n": 0, "correct": 0, "confusion": {}})
            dim["n"] += 1
            dim["correct"] += int(rec["ok"])
            if not rec["ok"]:
                key = f"{rec['expected']} -> {rec['got']}"
                dim["confusion"][key] = dim["confusion"].get(key, 0) + 1
        for dim in per_dim.values():
            dim["accuracy"] = round(dim["correct"] / dim["n"], 4) if dim["n"] else 0.0

        n = len(self.records)
        correct = sum(int(r["ok"]) for r in self.records)
        return {
            "n_cases": n,
            "accuracy": round(correct / n, 4) if n else 0.0,
            "per_dimension": per_dim,
        }

    def sections(self) -> dict:
        """Failures first, grouped per dimension, each one self-contained: the conversation,
        expected vs got, the oracle note, and the model's FULL reading of the turn
        (`model_read`) — schema-default values there (empty reason, confidence 0.5) are the
        anomaly signal that the model skipped a field rather than judged it."""
        failures: dict[str, list] = {}
        passes: dict[str, list] = {}
        for rec in self.records:
            if rec["ok"]:
                passes.setdefault(rec["dimension"], []).append(rec["case"])
            else:
                failures.setdefault(rec["dimension"], []).append({
                    "case": rec["case"],
                    "expected": rec["expected"],
                    "got": rec["got"],
                    "conversation": rec.get("conversation"),
                    "message": rec.get("message"),
                    "note": rec.get("note"),
                    "model_read": rec.get("model_read"),
                })
        return {"failures": failures, "passes": passes}

    def summary_lines(self, metrics: dict, prev: dict | None) -> list[str]:
        prev_dims = (prev or {}).get("per_dimension", {})
        lines = [
            f"  Cases: {metrics['n_cases']}   micro-accuracy: "
            f"{self.delta(metrics['accuracy'], (prev or {}).get('accuracy'))}",
            "",
        ]
        for name, dim in sorted(metrics["per_dimension"].items()):
            prev_acc = prev_dims.get(name, {}).get("accuracy")
            lines.append(f"  {name:18s} {dim['correct']:>2d}/{dim['n']:<2d}  "
                         f"{self.delta(dim['accuracy'], prev_acc)}")
            for rec in self.records:
                if rec["dimension"] == name and not rec["ok"]:
                    lines.append(f"  {'':18s}   ✗ {rec['case']}: "
                                 f"{rec['expected']} -> {rec['got']}")
        return lines
