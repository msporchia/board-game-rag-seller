from tests.e2e.enrichment.scorecard.row import Row


class Comparison:
    """The current-scorecard vs baseline comparison, one row per metric."""

    def __init__(self, rows: list[Row]):
        self.rows = rows

    @property
    def has_gating_regression(self) -> bool:
        return any(r.regressed and r.gate for r in self.rows)

    def regressions(self) -> list[Row]:
        return [r for r in self.rows if r.regressed and r.gate]

    def table(self) -> str:
        sym = {"improved": "improved", "regressed": "REGRESSED",
               "stable": "stable", "new": "new"}
        lines = [f"{'game':<18}{'metric':<24}{'base':<10}{'curr':<10}{'verdict'}"]
        for r in self.rows:
            gate = "" if r.gate else "  (info)"
            lines.append(f"{r.game:<18}{r.metric:<24}{str(r.baseline):<10}{str(r.current):<10}"
                         f"{sym.get(r.verdict, r.verdict)}{gate}")
        return "\n".join(lines)
