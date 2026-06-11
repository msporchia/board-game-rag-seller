"""RankingReport — scoring of the ranking eval (see eval_report.EvalReport)."""

import math

from tests.eval.report.eval_report import EvalReport


class RankingReport(EvalReport):
    """NDCG against an ORDERED oracle: how far is the actual ranking from the expected one.

    Each case carries an oracle ranking (the games that should be on the table, in order).
    The score is NDCG over the oracle-sized window — the slice of the ranking a customer
    actually sees — with graded relevance by oracle position (1st expected game weighs most).
    The discount makes the score behave the way the suite is read: a swap of adjacent games
    costs almost nothing (B,A,C,D vs A,B,C,D ≈ 0.95), the expected games sliding out of the
    window collapses it (D,?,?,? ≈ 0.14) — deviation is weighted by HOW FAR from the oracle,
    not just counted. `mean_displacement` (mean |actual − expected| position) is the
    diagnostic companion: it says how far the oracle items drifted, unweighted.

    The model under eval is the EMBEDDER — the only model in the loop (the corpus is the
    FROZEN post-pipeline fixture, the enrichment LLM already ran at freeze time).
    """

    prefix = "ranking"
    title = "GameRetriever — search() vs ordered oracle"
    measure = "NDCG@|oracle|"
    model_label = "embeddings"

    def model(self) -> str:
        try:
            from app.config import settings
            return settings.embedding_model
        except Exception:                   # noqa: BLE001  settings unavailable → unknown
            return "unknown"

    # ---- per-case scoring ----------------------------------------------------------

    def ndcg(self, rec: dict) -> float:
        """NDCG over the oracle-sized window; relevance = reversed oracle position."""
        window = len(rec["oracle"])
        rel = {item["id"]: window - item["expected_pos"] + 1 for item in rec["oracle"]}
        dcg = sum(rel[item["id"]] / math.log2(item["rank"] + 1)
                  for item in rec["oracle"] if item["rank"] <= window)
        idcg = sum((window - i) / math.log2(i + 2) for i in range(window))
        return dcg / idcg if idcg else 0.0

    def displacement(self, rec: dict) -> float:
        """Mean |actual − expected| position of the oracle items (unweighted drift)."""
        drifts = [abs(item["rank"] - item["expected_pos"]) for item in rec["oracle"]]
        return sum(drifts) / len(drifts)

    # ---- suite scoring --------------------------------------------------------------

    def aggregate(self) -> dict:
        n = len(self.records)
        scores = [self.ndcg(r) for r in self.records]
        return {
            "n_cases": n,
            "mean_ndcg": round(sum(scores) / n, 4) if n else 0.0,
            "perfect": sum(1 for s in scores if s > 0.999),
            "close": sum(1 for s in scores if s >= 0.8),
            "mean_displacement": round(sum(self.displacement(r) for r in self.records) / n, 2)
            if n else 0.0,
        }

    def sections(self) -> dict:
        """Failures (NDCG < 0.8) worst-first, each self-contained: the query, the expected
        order with the actual rank of every oracle game, and the window that actually came
        back — the intruders that beat the oracle are the anomaly signal."""
        failures = []
        passes = []
        for rec in sorted(self.records, key=self.ndcg):
            score = self.ndcg(rec)
            if score >= 0.8:
                passes.append({"case": rec["case"], "ndcg": round(score, 4)})
                continue
            failures.append({
                "case": rec["case"],
                "ndcg": round(score, 4),
                "mean_displacement": round(self.displacement(rec), 2),
                "query": rec["query"],
                "oracle": rec["oracle"],
                "window": rec["window"],
                "note": rec["note"],
            })
        return {"failures": failures, "passes": passes}

    def headline(self, metrics: dict) -> str:
        return (f"mean NDCG **{metrics['mean_ndcg']:.3f}** · {metrics['n_cases']} cases "
                f"({metrics['perfect']} perfect, {metrics['close']} ≥0.8)")

    def summary_lines(self, metrics: dict, prev: dict | None) -> list[str]:
        prev_disp = (prev or {}).get("mean_displacement")
        disp_note = f" (was: {prev_disp})" if prev_disp is not None else ""
        lines = [
            f"  Cases: {metrics['n_cases']}   mean NDCG: "
            f"{self.delta(metrics['mean_ndcg'], (prev or {}).get('mean_ndcg'))}",
            f"  Perfect: {metrics['perfect']}/{metrics['n_cases']}   "
            f"close (≥0.8): {metrics['close']}/{metrics['n_cases']}   "
            f"mean displacement: {metrics['mean_displacement']}{disp_note}",
            "",
        ]
        for rec in sorted(self.records, key=self.ndcg):
            score = self.ndcg(rec)
            mark = "✓" if score >= 0.8 else "✗"
            ranks = " ".join(f"#{item['rank']}" for item in rec["oracle"])
            lines.append(f"  {mark} {rec['case']:34s} ndcg {score:.3f}   oracle ranks: {ranks}")
        return lines
