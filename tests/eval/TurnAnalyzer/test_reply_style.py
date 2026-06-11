"""TurnAnalyzer — `reply_style` dimension EVAL (real LLM, baseline measurement).

Reply style reads HOW the customer writes (terse vs rich/descriptive), independently of
mood: in the routing (`app/chat/routing.py`) a short style nudges toward the concrete
QUICK_MATCH/GUIDED stance, and downstream the generate step mirrors the customer's verbosity.

The fixtures keep mood out of the label and include the mirror boundary case: a LONG but
unenthusiastic message (a rambling, dutiful gift hunt) that must score `long` — the twin of
the short-but-excited case in the enthusiasm suite, keeping the two dimensions separable.

No correctness assert yet: the first runs establish the baseline; scoring and the diff vs
the previous run live in conftest (`record_analysis` + `pytest_sessionfinish`).

    docker exec seller-api python -m pytest tests/eval/TurnAnalyzer/test_reply_style.py -q
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.llm

FIXTURE = Path(__file__).parent / "fixtures" / "reply_style_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
IDS = [c["id"] for c in CASES]


class TestReplyStyle:
    """8 cases, 4 per label (short/long), each emphasizing verbosity only."""

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_case(self, analyzer, case, record_analysis):
        analysis = analyzer(case["history"], case["message"])
        record_analysis({
            "case": case["id"],
            "dimension": "reply_style",
            "expected": case["expect"],
            "got": analysis.reply_style,
            "ok": analysis.reply_style == case["expect"],
            "note": case["note"],
            "conversation": case["history"],
            "message": case["message"],
            "model_read": analysis.model_dump(),
        })
