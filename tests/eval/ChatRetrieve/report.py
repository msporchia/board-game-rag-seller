"""RetrieveReport — scoring of the retrieve eval (see eval_report.EvalReport)."""

from tests.eval.report.eval_report import EvalReport


class RetrieveReport(EvalReport):
    """recall@k + mean rank of the found targets, with every case as a readable line.

    The summary is fully per-case (hit or miss, rank, k): retrieval tuning means looking at
    which conversation missed, so each line names its case (full record, including the oracle
    note, in `runs/last.json`). The model under eval here is the EMBEDDER — the only model in
    the loop, hence the header override.
    """

    prefix = "retrieve"
    title = "ChatRetrieve — _retrieve"
    measure = "recall@k"
    model_label = "embeddings"

    def model(self) -> str:
        try:
            from app.config import settings
            return settings.embedding_model
        except Exception:                   # noqa: BLE001  settings unavailable → unknown
            return "unknown"

    def aggregate(self) -> dict:
        n = len(self.records)
        found = [r["rank"] for r in self.records if r["rank"] is not None]
        hits = sum(int(r["hit"]) for r in self.records)
        return {
            "n_cases": n,
            "recall_at_k": round(hits / n, 4) if n else 0.0,
            "found": len(found),
            "mean_rank": round(sum(found) / len(found), 2) if found else None,
        }

    def summary_lines(self, metrics: dict, prev: dict | None) -> list[str]:
        prev_rank = (prev or {}).get("mean_rank")
        rank_note = f" (was: {prev_rank})" if prev_rank is not None else ""
        lines = [
            f"  Cases: {metrics['n_cases']}   recall@k: "
            f"{self.delta(metrics['recall_at_k'], (prev or {}).get('recall_at_k'))}",
            f"  Found: {metrics['found']}/{metrics['n_cases']}   "
            f"mean rank of found: {metrics['mean_rank']}{rank_note}",
            "",
        ]
        for rec in self.records:
            mark = "✓" if rec["hit"] else "✗"
            rank = rec["rank"] if rec["rank"] is not None else "—"
            lines.append(f"  {mark} {rec['case']:38s} rank {rank!s:>2s} / k={rec['k_used']}")
        return lines
