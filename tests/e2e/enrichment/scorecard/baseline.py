import json
from dataclasses import asdict
from pathlib import Path

from tests.e2e.enrichment.scorecard.comparison import Comparison
from tests.e2e.enrichment.scorecard.row import Row
from tests.e2e.enrichment.scorecard.scorecard import Scorecard
from tests.e2e.enrichment.scorecard.spec import METRIC_SPECS

BASELINE_PATH = Path(__file__).resolve().parents[1] / "baseline.json"


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
                                spec.verdict(base[spec.key], c), spec.gate))
        return Comparison(rows)

    @classmethod
    def write(cls, scorecard: Scorecard, path: Path = BASELINE_PATH) -> None:
        path.write_text(json.dumps(scorecard.to_dict(), ensure_ascii=False, indent=2),
                        encoding="utf-8")
