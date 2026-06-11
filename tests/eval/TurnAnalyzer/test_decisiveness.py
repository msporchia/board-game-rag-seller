"""TurnAnalyzer — `decisiveness` EVAL: per-case oracle labels on a real LLM.

WHAT THIS DIMENSION DRIVES
--------------------------
`decisiveness` is the single highest-leverage signal in the strategy router
(`app.chat.routing.pick_strategy`): `decided` short-circuits straight to QUICK_MATCH
(immediate concrete proposals), and `moderate` is the tiebreaker that turns a
low-enthusiasm/short-replies turn into QUICK_MATCH instead of GUIDED. Misreading this
dimension changes WHAT the shop assistant does next turn, not just how it phrases it.

VENIAL VS GRAVE CONFUSIONS
--------------------------
- `undecided <-> moderate` is venial: both usually land on guiding strategies, the
  conversation keeps narrowing down and self-corrects within a turn or two.
- `moderate -> decided` is borderline-grave: it triggers a premature pitch to a customer
  who still wanted to compare options.
- The polar confusions `undecided <-> decided` are grave: pitching hard at a lost
  customer (pushy salesperson) or stalling a customer who already named the game they
  want to buy (lost sale).

Each fixture conversation emphasizes decisiveness while keeping enthusiasm, expertise
and reply style as neutral as possible, so this dimension is weighed alone. There is no
correctness assert: the first runs establish the baseline; the conftest aggregates the
records into the per-dimension summary and the confusion matrix at session end.

    docker exec seller-api python -m pytest tests/eval/TurnAnalyzer/test_decisiveness.py -q
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.llm

FIXTURE = Path(__file__).parent / "fixtures" / "decisiveness_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
IDS = [c["id"] for c in CASES]


class TestDecisiveness:
    """12 oracle-labeled conversations (4 per label), recorded for the session report."""

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_case(self, analyzer, case, record_analysis):
        """Run the production-shaped analyze call and record expected vs got (no assert:
        baseline measurement first, thresholds come after the numbers are in)."""
        analysis = analyzer(case["history"], case["message"])
        record_analysis({
            "case": case["id"],
            "dimension": "decisiveness",
            "expected": case["expect"],
            "got": analysis.decisiveness,
            "ok": analysis.decisiveness == case["expect"],
            "note": case["note"],
        })
