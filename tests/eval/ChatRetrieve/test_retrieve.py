"""ChatRetrieve — recall@k of the chat's RETRIEVE node over multi-turn conversations.

WHAT IS UNDER EVAL
------------------
`ChatGraph._retrieve` is the production query-assembly + hybrid-search step: it folds the
previous user turns into the query (the current message may be vague — "scegli tu" — while the
identifying information sits two turns back), parses quick-reply clicks into hard SearchFilters
(falling back to query leftovers for free-form clicks), and lets the strategy decide k
(GUIDED 2, QUICK_MATCH 4, DISCOVERY honors the request's k). The analysis dimensions and the
strategy routing are assumed correct by construction here — they have their own evals/units;
this suite asks one question: given the conversation, does the right game reach the table?

WHY THE PRIVATE NODE
--------------------
The test deliberately calls the PRIVATE `graph._retrieve(state)` instead of replaying the query
assembly in test code: re-deriving query/filters/k here would duplicate the very logic under
eval and silently drift from production. The only production behavior the test mirrors is the
analyze node's history contribution (the current message is appended as the last "utente:"
line before retrieve runs), because that is graph-runtime plumbing, not retrieve logic.

The interesting fixtures SPLIT the identifying information across turns (player count in turn 1,
theme in turn 3), so a single-message search could not pass them: they measure that the query
assembly actually carries the conversation. There is no correctness assert: the first runs
establish the baseline; the conftest aggregates recall@k and mean rank at session end.

    docker exec seller-api python -m pytest tests/eval/ChatRetrieve -q
"""

import json
from pathlib import Path

import pytest

from app.chat.models.strategy import Strategy
from app.chat.routing import STRATEGY_K

pytestmark = pytest.mark.llm

FIXTURE = Path(__file__).parent / "fixtures" / "retrieve_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
IDS = [c["id"] for c in CASES]


class TestRetrieve:
    """Oracle-labeled conversations: the expected game must reach the strategy's top-k."""

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_case(self, graph, case, record_retrieval):
        """Run the production node on a ChatState-shaped dict and record the target's rank."""
        # In production the analyze node appends "utente: <message>" to history BEFORE
        # retrieve runs (and _retrieve drops that last user turn when picking the previous
        # context); mirror that contribution so the state is exactly retrieve-time shaped.
        state = {
            "message": case["message"],
            "choices": case["choices"],
            "k": case["k"],
            "history": [*case["history"], f"utente: {case['message']}"],
            "filters_spec": {},
            "strategy": case["strategy"],
        }
        out = graph._retrieve(state)

        # k as the node computed it (production constants, not re-derived logic).
        strategy = Strategy(case["strategy"])
        k_used = (case["k"] or 5) if strategy is Strategy.DISCOVERY else STRATEGY_K[strategy]
        rank = next((i + 1 for i, hit in enumerate(out["hits"])
                     if hit.id_product == case["expect_id"]), None)
        record_retrieval({
            "case": case["id"],
            "expected_id": case["expect_id"],
            "k_used": k_used,
            "rank": rank,
            "hit": rank is not None and rank <= k_used,
            "note": case["note"],
            "conversation": case["history"],
            "message": case["message"],
            "choices": case["choices"],
            # who beat the target: the anomaly signal (hub documents, diluted queries)
            "top_hits": [{"id": h.id_product, "name": h.name} for h in out["hits"]],
        })
