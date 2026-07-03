"""ChatConversation — EVAL of full multi-turn conversations on the production graph.

WHAT IS MEASURED AND WHY
------------------------
The per-node suites answer "does each step work in isolation" (TurnAnalyzer: the user reading,
ChatRetrieve: the query assembly, ChatPitch: the grounded generation). This suite answers the
question none of them can: given a REAL conversation — state accumulating turn over turn, the
analyze output steering the router, clicks merging into filters, the history feeding retrieval
— does the session converge to a sensible recommendation, and does the trajectory respect the
product rules along the way?

THE CASE TAXONOMY (fixtures/conversation_cases.json, oracle rationale in each `note`)
-------------------------------------------------------------------------------------
- vague→specific convergence, incl. the distractor trap (turn 1 favors a confounder, the turn-2
  detail must re-rank toward the target);
- out-of-catalog title → a hand-curated set of acceptable alternatives (grounding makes showing
  the absent title impossible; the eval checks the fallback is SENSIBLE, not just clean);
- constraint reversal (the latest click on a dimension must replace, not pile up);
- decided customer at turn 1 (straight to QUICK_MATCH, no guidance loop);
- stalling customer (the forced-proposal rule: a concrete proposal by turn 4 at the latest);
- infeasible constraints → honest no-match, then recovery when a constraint is relaxed;
- clicks mixed with free text (hard filter + query signal in the same turn).

ORACLES (all rule-based, no LLM judge)
--------------------------------------
Per turn (each optional, declared per case): `strategy_in` (the routed strategy), `min_games`,
`no_match` (the honest empty reply). Per case: `accept_ids`/`by_turn` (convergence: any
accepted game recommended within the turn budget), `filters` (subset of the final
filters_spec), `proposal_by_turn` (some turn routed to a proposal strategy in time). Everything
else recorded per turn (analysis dimensions, escalation, fallback, games on the table) is
trajectory data for the run file, not an oracle. No assert: the first runs establish the
baseline, rates ARE the deliverable — same stance as the other suites.

ENGINE ARMS (docs/idee.md §Q): the suite is the arbiter between engines — the conftest builds
the arm `CHAT_ENGINE` selects over the same fixtures. Strategy-shaped oracles (`strategy_in`,
`proposal_by_turn`) apply only to engines that ROUTE strategies: an arm without the router
(piloted) leaves `strategy` unset in state, and those checks are out of scope for it, like any
oracle a case does not declare. Each conversation also records its LLM calls and Ollama token
counts (the session-wide LLMUsageTracker, snapshotted around the case) so RESULTS compares
arms as Δquality next to Δcost.

FALLBACK DETECTION
------------------
Same external reconstruction as ChatPitch (see its module docstring): a turn is classified as
fallback iff the response is byte-identical to `ChatAdvisor._fallback(hits)` over the hits the
state had on the table that turn. The empty no-match reply is NOT a fallback.

    docker exec seller-api python -m pytest tests/eval/ChatConversation -q
"""

import json
from pathlib import Path

import pytest

from tests.eval.ChatConversation.conversation_driver import ConversationDriver

pytestmark = pytest.mark.llm

FIXTURE = Path(__file__).parent / "fixtures" / "conversation_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
IDS = [c["id"] for c in CASES]


class TestConversation:
    """Scripted conversations replayed through graph.reply(), one session per case; after each
    turn the checkpointed state is read back (graph.state) — the per-turn 'spying' that turns
    strategy, filters and analysis into recordable trajectory data.

    The turn loop and the oracle scoring live in `ConversationDriver` (conversation_driver.py):
    factored out so the strong-model simulation harness (simulation/run.py) replays the exact
    same driver over an engine wired with FileExchange* LLMs instead of Ollama — the comparison
    is only meaningful if both arms are scored by the identical oracle.
    """

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_case(self, graph, case, record_conversation, llm_usage):
        record_conversation(ConversationDriver().run(graph, case, llm_usage))
