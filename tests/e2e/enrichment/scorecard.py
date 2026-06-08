"""Scorecard + Baseline — the clear "improved/regressed" signal.

`Scorecard` reduces a `RunResult` to stable, serializable metrics. `Baseline` is the reference
snapshot versioned on git (`baseline.json`): it compares the current scorecard with tolerances and
says, per metric, improved / regressed / stable.

Philosophy (regression/golden testing — see README):
  - baseline VERSIONED on git: updated only on purpose (`Baseline.write`), never by hand; git
    history becomes the quality trend over time.
  - tolerances, not equalities: the LLM/embeddings aren't bit-deterministic. The GATE rides on
    ROBUST metrics — recall@K (queries reaching the first screen) and the boolean web_fired —
    while raw ranks are noisy and kept INFORMATIONAL only.
  - gate: a regression beyond tolerance on a "gate" metric fails the suite.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.rag.retriever import GameRetriever
from tests.e2e.enrichment.harness import RunResult

BASELINE_PATH = Path(__file__).resolve().parent / "baseline.json"
SCREEN_K = 10        # first screen: top-K out of ~50 games
RANK_DEPTH = 50      # how deep we look for the game when assigning it a rank


def rank(retriever: GameRetriever, query: str, id_product: int, depth: int = RANK_DEPTH) -> int:
    """1-based position of the game in the results; `depth+1` if it doesn't appear."""
    for i, h in enumerate(retriever.search(query, k=depth), 1):
        if h.id_product == id_product:
            return i
    return depth + 1


@dataclass
class GameMetrics:
    """A single game's metrics (all serializable)."""

    web_fired: bool
    n_extractions: int
    embed_len_full: int
    embed_len_base: int
    avg_rank_full: float
    avg_rank_base: float
    queries_in_screen_full: int
    n_queries: int
    ranks_full: list[int] = field(default_factory=list)
    ranks_base: list[int] = field(default_factory=list)


@dataclass
class MetricSpec:
    """How to compare a metric against the baseline."""

    key: str
    direction: str          # "lower" (less is better) | "higher" | "exact"
    tol: float = 0.0        # change tolerated before calling it improved/regressed
    gate: bool = True       # whether a regression on this metric fails the suite


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


class Scorecard:
    """A run's per-game metrics, derived from the real retrievers."""

    def __init__(self, screen_k: int, games: dict[str, GameMetrics]):
        self.screen_k = screen_k
        self.games = games

    @classmethod
    def from_result(cls, result: RunResult, screen_k: int = SCREEN_K) -> "Scorecard":
        games: dict[str, GameMetrics] = {}
        for c in result.cases:
            queries = c.must_find_queries
            rf = [rank(result.retriever_full, q, c.id_product) for q in queries]
            rb = [rank(result.retriever_base, q, c.id_product) for q in queries]
            n = len(queries) or 1
            games[c.slug] = GameMetrics(
                web_fired=c.query in result.served_queries,
                n_extractions=len(result.store.get_extractions(c.id_product)),
                embed_len_full=len(result.full_docs[c.id_product].embed_text or ""),
                embed_len_base=len(result.base_embed[c.id_product]),
                avg_rank_full=round(sum(rf) / n, 2),
                avg_rank_base=round(sum(rb) / n, 2),
                queries_in_screen_full=sum(1 for r in rf if r <= screen_k),
                n_queries=len(queries),
                ranks_full=rf,
                ranks_base=rb,
            )
        return cls(screen_k, games)

    def to_dict(self) -> dict:
        return {"screen_k": self.screen_k,
                "games": {slug: asdict(m) for slug, m in self.games.items()}}

    def table(self) -> str:
        lines = [f"SCORECARD (screen_k={self.screen_k})",
                 f"{'game':<20}{'web':<6}{'in_screen':<11}{'avg_full':<10}{'avg_base':<10}{'extr':<6}{'len_f/len_b'}"]
        for slug, m in self.games.items():
            lines.append(
                f"{slug:<20}{str(m.web_fired):<6}{f'{m.queries_in_screen_full}/{m.n_queries}':<11}"
                f"{m.avg_rank_full:<10}{m.avg_rank_base:<10}{m.n_extractions:<6}"
                f"{m.embed_len_full}/{m.embed_len_base}")
        return "\n".join(lines)


@dataclass
class Row:
    game: str
    metric: str
    baseline: object
    current: object
    verdict: str            # "improved" | "regressed" | "stable" | "new"
    gate: bool

    @property
    def regressed(self) -> bool:
        return self.verdict == "regressed"


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


def _verdict(spec: MetricSpec, base, cur) -> str:
    if spec.direction == "exact":
        return "stable" if cur == base else "regressed"
    delta = cur - base
    worse = delta > spec.tol if spec.direction == "lower" else delta < -spec.tol
    better = delta < -spec.tol if spec.direction == "lower" else delta > spec.tol
    if worse:
        return "regressed"
    if better:
        return "improved"
    return "stable"


class Baseline:
    """The reference snapshot versioned on git."""

    def __init__(self, data: dict, path: Path = BASELINE_PATH):
        self.data = data
        self.path = path

    @classmethod
    def load(cls, path: Path = BASELINE_PATH) -> "Baseline | None":
        if not path.exists():
            return None
        return cls(json.loads(path.read_text(encoding="utf-8")), path)

    def compare(self, scorecard: Scorecard) -> Comparison:
        base_games = self.data.get("games", {})
        rows: list[Row] = []
        for slug, m in scorecard.games.items():
            cur = asdict(m)
            base = base_games.get(slug)
            for spec in METRIC_SPECS:
                c = cur[spec.key]
                if base is None or spec.key not in base:
                    rows.append(Row(slug, spec.key, "-", c, "new", spec.gate))
                    continue
                rows.append(Row(slug, spec.key, base[spec.key], c,
                                _verdict(spec, base[spec.key], c), spec.gate))
        return Comparison(rows)

    @classmethod
    def write(cls, scorecard: Scorecard, path: Path = BASELINE_PATH) -> None:
        path.write_text(json.dumps(scorecard.to_dict(), ensure_ascii=False, indent=2),
                        encoding="utf-8")
