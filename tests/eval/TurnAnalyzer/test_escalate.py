"""TurnAnalyzer — `escalate` dimension EVAL (REAL LLM).

WHY THIS DIMENSION MATTERS
--------------------------
`escalate` is the model-tiering contract (see `TurnAnalysis` and `ChatGraph._analyze`): when
True, the generate step switches to `settings.llm_model_strong`. Per the prompt, it must be
True ONLY for complex conversations or purchase-ready customers (budget, player count,
urgency). Both error directions cost real money or real customers:

  - false POSITIVE → the expensive model is burned on idle browsing / small talk;
  - false NEGATIVE → a purchase-ready customer gets the weak model at the exact moment the
    answer quality decides the sale.

ORACLE (`fixtures/escalate_cases.json`)
---------------------------------------
10 hand-written conversations, 5 expecting True / 5 expecting False, each crafted to emphasize
this dimension only. Both sides include a boundary case (a budget mentioned while daydreaming
→ False; immediate purchase intent without a budget → True).

`escalation_reason` and `confidence` are recorded in the report for human inspection but NOT
scored. There is no correctness assert yet: the first runs establish the baseline, the diff vs
the previous run (printed by the conftest) flags regressions.

    docker exec seller-api python -m pytest tests/eval/TurnAnalyzer/test_escalate.py -q
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.llm

FIXTURE = Path(__file__).parent / "fixtures" / "escalate_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
IDS = [c["id"] for c in CASES]


class TestEscalate:
    """Binary accuracy over 10 cases; reason/confidence recorded for inspection only."""

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_escalate_case(self, analyzer, case, record_analysis):
        """One production-shaped analyze call per case; the record feeds the run report
        (no threshold assertion: baseline measurement first)."""
        analysis = analyzer(case["history"], case["message"])
        record_analysis({
            "case": case["id"],
            "dimension": "escalate",
            "expected": case["expect"],
            "got": analysis.escalate,
            "ok": analysis.escalate == case["expect"],
            "note": case["note"],
            "escalation_reason": analysis.escalation_reason,
            "confidence": analysis.confidence,
        })
