"""TurnAnalyzer — `expertise_level` EVAL: how well the analyzer reads the customer's level.

WHAT THIS DIMENSION DRIVES DOWNSTREAM
-------------------------------------
The analysis prompt (`ChatGraph._analysis_prompt`) ties expertise to the TERMS the customer
uses ("worker placement" → advanced; "un gioco da fare in famiglia" with no technical terms →
beginner). The label then shapes two things:

  - the advisor persona (`app/chat/advisor.py`, `_EXPERTISE_RULES`): beginner → simple
    language, every technical term explained; advanced → precise terminology (worker
    placement, engine building, area control, ...);
  - the routing (`app/chat/routing.py`, `pick_strategy` rule 3): a high-enthusiasm beginner
    goes to EXPLANATORY instead of DISCOVERY, because they need the mechanics explained
    before free-form exploration lands.

WHICH CONFUSIONS MATTER
-----------------------
Adjacent misses are venial: beginner→intermediate (or advanced→intermediate) just makes the
pitch a notch off. The grave miss is beginner→advanced: the advisor throws hobbyist jargon at
a novice — for a salesperson, that is a lost customer. The confusion matrix in the session
report (see conftest) is where this difference shows.

ORACLE (`fixtures/expertise_cases.json`)
----------------------------------------
12 hand-written conversations, 4 per label, each crafted to emphasize expertise while keeping
the other dimensions neutral. `intermediate` is the hard label (mainstream titles, imprecise
semi-technical wording); the set includes boundary cases such as a beginner who name-drops a
famous title without understanding it.

No correctness assert yet: the first runs establish the baseline, the diff vs the previous
run (printed by conftest's `pytest_sessionfinish`) flags regressions.

    docker exec seller-api python -m pytest tests/eval/TurnAnalyzer/test_expertise.py -q
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.llm

FIXTURE = Path(__file__).parent / "fixtures" / "expertise_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
IDS = [c["id"] for c in CASES]


class TestExpertise:
    """One analyze call per case; the label goes into the session report, not an assert."""

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_expertise_case(self, analyzer, case, record_analysis):
        analysis = analyzer(case["history"], case["message"])
        record_analysis({
            "case": case["id"],
            "dimension": "expertise_level",
            "expected": case["expect"],
            "got": analysis.expertise_level,
            "ok": analysis.expertise_level == case["expect"],
            "note": case["note"],
            "conversation": case["history"],
            "message": case["message"],
            "model_read": analysis.model_dump(),
        })
