from dataclasses import dataclass


@dataclass
class MetricSpec:
    """How to compare a metric against the baseline."""

    key: str
    direction: str          # "lower" (less is better) | "higher" | "exact"
    tol: float = 0.0        # change tolerated before calling it improved/regressed
    gate: bool = True       # whether a regression on this metric fails the suite

    def verdict(self, base, cur) -> str:
        """Compare a value against the baseline: improved / regressed / stable."""
        if self.direction == "exact":
            return "stable" if cur == base else "regressed"
        delta = cur - base
        worse = delta > self.tol if self.direction == "lower" else delta < -self.tol
        better = delta < -self.tol if self.direction == "lower" else delta > self.tol
        if worse:
            return "regressed"
        if better:
            return "improved"
        return "stable"


# order is also the print order. The gate rides on web_fired (exact) + recall@K (queries reaching
# the first screen, tolerating a 1-query wobble from LLM non-determinism). avg_rank is too noisy
# to gate on (a single query can swing ±20 between runs) → informational.
METRIC_SPECS = [
    MetricSpec("web_fired", "exact", gate=True),
    MetricSpec("queries_in_screen_full", "higher", tol=1, gate=True),
    MetricSpec("avg_rank_full", "lower", tol=2.0, gate=False),    # informational (noisy)
    MetricSpec("n_extractions", "higher", tol=0, gate=False),     # informational
    MetricSpec("embed_len_full", "higher", tol=0, gate=False),    # diagnostic (Synth budget)
]
