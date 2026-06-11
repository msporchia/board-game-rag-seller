"""TurnAnalyzer — `enthusiasm` dimension EVAL (real LLM, baseline measurement).

Enthusiasm reads how INVOLVED the customer is, independently of how decided or expert they
are: it drives the strategy routing (`app/chat/routing.py`) — high enthusiasm opens up
DISCOVERY (or EXPLANATORY for beginners), low enthusiasm pushes toward the concrete
QUICK_MATCH/GUIDED stance that gets a disengaged customer to a proposal fast.

The fixtures emphasize involvement only (decisiveness/expertise kept neutral) and include
the critical boundary case: a SHORT but clearly enthusiastic message ("Bellissimo! Lo
voglio!") that must score `high` despite its brevity — that is what separates this
dimension from `reply_style`.

No correctness assert yet: the first runs establish the baseline; scoring and the diff vs
the previous run live in conftest (`record_analysis` + `pytest_sessionfinish`).

    docker exec seller-api python -m pytest tests/eval/TurnAnalyzer/test_enthusiasm.py -q
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.llm

FIXTURE = Path(__file__).parent / "fixtures" / "enthusiasm_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
IDS = [c["id"] for c in CASES]


class TestEnthusiasm:
    """12 cases, 4 per label (low/medium/high), each emphasizing involvement only."""

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_case(self, analyzer, case, record_analysis):
        analysis = analyzer(case["history"], case["message"])
        record_analysis({
            "case": case["id"],
            "dimension": "enthusiasm",
            "expected": case["expect"],
            "got": analysis.enthusiasm,
            "ok": analysis.enthusiasm == case["expect"],
            "note": case["note"],
        })
