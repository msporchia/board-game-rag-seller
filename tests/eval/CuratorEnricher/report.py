"""CuratorReport — scoring of the Curator assess eval (see eval_report.EvalReport)."""

from tests.eval.report.eval_report import EvalReport


class CuratorReport(EvalReport):
    """Slot-filling P/R/F-β (TAC KBP / TREC IE), plus per-case slot misses as readable lines.

    F0.5/F0.25 favor precision because a wrong extraction (FP) pollutes the data, while an FN
    just leaves the field missing. The summary lists each FP/FN as `slug.slot` with the LLM
    value — tuning opens one case at a time (full record in `runs/last.json`).
    """

    prefix = "assess"
    title = "Curator — assess()"
    measure = "slot-filling scoring"

    def aggregate(self) -> dict:
        total = {"TP": 0, "FP": 0, "FN": 0, "TN": 0, "SKIP": 0}
        per_slot: dict[str, dict] = {}
        for rec in self.records:
            for k, v in rec.get("counts", {}).items():
                total[k] += v
            for slot, info in rec.get("per_slot", {}).items():
                slot_counts = per_slot.setdefault(
                    slot, {"TP": 0, "FP": 0, "FN": 0, "TN": 0, "SKIP": 0})
                slot_counts[info["outcome"]] += 1

        p = self._safe_div(total["TP"], total["TP"] + total["FP"])
        r = self._safe_div(total["TP"], total["TP"] + total["FN"])
        return {
            "counts": total,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(self._f_beta(p, r, 1.0), 4),
            "f0_5": round(self._f_beta(p, r, 0.5), 4),    # precision weighs 4× more
            "f0_25": round(self._f_beta(p, r, 0.25), 4),  # precision weighs 16× more
            "per_slot": per_slot,
        }

    @staticmethod
    def _safe_div(num: float, den: float) -> float:
        return num / den if den else 0.0

    @classmethod
    def _f_beta(cls, p: float, r: float, beta: float) -> float:
        """F-β = (1+β²)·P·R / (β²·P + R). β<1 favors precision, β>1 favors recall."""
        b2 = beta * beta
        return cls._safe_div((1 + b2) * p * r, b2 * p + r)

    def sections(self) -> dict:
        """Failures first: one entry per case with FP/FN slots, each slot with the oracle and
        the LLM value side by side — enough to judge the extraction without rerunning."""
        failures = []
        passes = []
        for rec in self.records:
            missed = {slot: {"outcome": info["outcome"], "oracle": info.get("oracle"),
                             "llm_value": info.get("llm_value")}
                      for slot, info in rec.get("per_slot", {}).items()
                      if info["outcome"] in ("FP", "FN")}
            if missed:
                failures.append({"case": rec["slug"], "slots": missed})
            else:
                passes.append(rec["slug"])
        return {"failures": failures, "passes": passes}

    def summary_lines(self, metrics: dict, prev: dict | None) -> list[str]:
        c = metrics["counts"]
        n_eval = c["TP"] + c["FP"] + c["FN"] + c["TN"]
        lines = [
            f"  Slots evaluated: {n_eval} (skip structurally-present: {c['SKIP']})",
            f"  TP={c['TP']}  FP={c['FP']}  FN={c['FN']}  TN={c['TN']}",
            "",
        ]
        pm = prev or {}
        for label, key in (("Precision", "precision"), ("Recall", "recall"),
                           ("F1       ", "f1"), ("F0.5     ", "f0_5"),
                           ("F0.25    ", "f0_25")):
            lines.append(f"  {label}: {self.delta(metrics[key], pm.get(key))}")
        lines.append("")
        lines.append(f"  {'slot':28s}  {'TP':>3s} {'FP':>3s} {'FN':>3s} {'TN':>3s}")
        for slot, sc in metrics["per_slot"].items():
            lines.append(f"  {slot:28s}  {sc['TP']:>3d} {sc['FP']:>3d} "
                         f"{sc['FN']:>3d} {sc['TN']:>3d}")

        misses = [(rec["slug"], slot, info)
                  for rec in self.records
                  for slot, info in rec.get("per_slot", {}).items()
                  if info["outcome"] in ("FP", "FN")]
        if misses:
            lines.append("")
            for slug, slot, info in misses:
                value = str(info.get("llm_value"))[:60]
                detail = f' (llm: "{value}")' if info["outcome"] == "FP" else ""
                lines.append(f"  ✗ {slug}.{slot}: {info['outcome']}{detail}")
        return lines
