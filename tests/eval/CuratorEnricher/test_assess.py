"""CuratorEnricher — `assess()` EVAL: quantitative scoring (slot-filling) on a real LLM.

PURPOSE
-------
Measure the step's 3 things (classification + extraction + normalization) with the STANDARD
slot-filling metric (TAC KBP / TREC IE): TP/FP/FN/TN per slot, aggregated into
**Precision / Recall / F-β**. Not LLM-as-judge (it would require a powerful model and
re-introduce non-determinism): deterministic substring matching.

METRIC WEIGHTS
--------------
For our 7 slots, we report F1 (balanced), F0.5 (precision-favored, FP weighs 4× more than FN),
F0.25 (aggressively precision-favored, FP weighs 16×). The choice of β depends on how
pessimistic we want to be about FP (a wrong extraction = polluted data → worse than an FN that
leaves the field missing). The acceptance threshold is decided AFTER seeing the baseline (for
now no threshold assert: the test prints the numbers, the diff vs the previous run flags
regressions).

ORACLE (`expect` in `fixtures/assess_cases.json`)
-------------------------------------------------
For each slot:
  - list `["substr", ...]` → gold PRESENT: the extraction is valid if the value contains at
    least one substring (case-insensitive). Stripped structured ones → automatic oracle from
    the original DTO; descriptive ones → hand-curated.
  - `null`                → gold ABSENT: the slot must be in `mancanti` (any extraction is an
    FP from invention).
  - `"__STRUCT_PRESENT__"` → the slot is in the DTO's CERTAIN DATA: the LLM is not called, we
    skip scoring (not relevant to measuring the Curator).

PER-SLOT OUTCOME
----------------
  TP  extracted, value contains at least one acceptable substring
  FP  extracted, value contains NO substring (even if gold ABSENT)
  FN  in mancanti, but the gold was PRESENT
  TN  in mancanti, and the gold was ABSENT
  -   skip (gold = __STRUCT_PRESENT__)

The per-slot details (including the per-case TP/FP/FN diff) end up in the persistent report
`runs/<timestamp>.json` (`record_assess` fixture); the summary + diff vs the previous run is
printed by `pytest_sessionfinish` (see conftest).

    docker exec seller-api python -m pytest tests/eval/CuratorEnricher -q
"""

import json
import os
from pathlib import Path

import pytest

from app.ingestion.enricher.curator import CuratorEnricher
from app.ingestion.sources.json_source import JsonSource

pytestmark = pytest.mark.llm

FIXTURE = Path(__file__).parent / "fixtures" / "assess_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
# Quick iteration: EVAL_LIMIT=N runs only the first N cases (the LLM is slow on CPU).
# Unset → the full suite. The metrics are still printed, just over fewer cases.
_limit = os.environ.get("EVAL_LIMIT")
if _limit:
    CASES = CASES[: int(_limit)]
IDS = [c["slug"] for c in CASES]


@pytest.fixture(scope="module")
def curator():
    return CuratorEnricher()


def _value_matches(value, acceptable: list[str]) -> bool:
    """True if `value` (str or list[str]) contains at least one of the substrings (case-insens)."""
    if value is None:
        return False
    if isinstance(value, list):
        text = " ".join(value).lower()
    else:
        text = str(value).lower()
    return any(s.lower() in text for s in acceptable)


def _score_slot(slot_oracle, llm_value_or_none) -> str:
    """Classifies the outcome of ONE slot into TP/FP/FN/TN/SKIP per the oracle schema."""
    if slot_oracle == "__STRUCT_PRESENT__":
        return "SKIP"
    if slot_oracle is None:                              # gold ABSENT
        return "FP" if llm_value_or_none is not None else "TN"
    # gold PRESENT (list of acceptable substrings)
    if llm_value_or_none is None:
        return "FN"
    return "TP" if _value_matches(llm_value_or_none, slot_oracle) else "FP"


class TestCuratorAssess:
    """Slot-filling scoring over 10 cases: TP/FP/FN/TN per slot, reported in the report."""

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_score_case(self, curator, case, record_assess):
        """For each case, we compute the outcome for each of the 7 slots and record it in the
        report (there's no threshold assertion: we measure the baseline first)."""
        doc = JsonSource([case["dto"]]).fetch()[0]
        a = curator.assess(doc)
        estratti = a.get("estratti", {})

        per_slot = {}
        counts = {"TP": 0, "FP": 0, "FN": 0, "TN": 0, "SKIP": 0}
        for slot, oracle in case["expect"].items():
            llm_val = estratti.get(slot)
            outcome = _score_slot(oracle, llm_val)
            counts[outcome] += 1
            per_slot[slot] = {"outcome": outcome, "oracle": oracle,
                              "llm_value": llm_val if outcome != "SKIP" else None}

        record_assess({
            "slug": case["slug"],
            "expect": case["expect"],
            "llm_output": a,
            "per_slot": per_slot,
            "counts": counts,
            "verdict": "PASS",   # no fail for now: baseline measurement
            "errors": [],
        })
