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

from app.chat.advisor import ChatAdvisor
from app.chat.models.response import ChatResponse
from app.models.game_hit import GameHit

pytestmark = pytest.mark.llm

FIXTURE = Path(__file__).parent / "fixtures" / "conversation_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))
IDS = [c["id"] for c in CASES]

_PROPOSAL = {"QUICK_MATCH", "DISCOVERY"}


def _is_fallback(response: ChatResponse, hits: list[GameHit]) -> bool:
    """True iff `response` is byte-identical to `ChatAdvisor._fallback(hits)` (the ChatPitch
    reconstruction, over the hits the graph state had on the table this turn)."""
    return bool(hits) and (
        response.message == ChatAdvisor._plain_pitch(hits[:3])
        and response.quick_replies == []
        and [g.id_product for g in response.games] == [h.id_product for h in hits[:3]]
    )


def _turn_checks(expect: dict, strategy: str, response: ChatResponse) -> list[tuple[str, bool]]:
    """Evaluate the per-turn oracles a case declares; absent keys are out of scope — and so is
    `strategy_in` when the engine has no strategy router (state leaves `strategy` unset)."""
    checks = []
    if "strategy_in" in expect and strategy is not None:
        checks.append(("strategy_in", strategy in expect["strategy_in"]))
    if "min_games" in expect:
        checks.append(("min_games", len(response.games) >= expect["min_games"]))
    if "no_match" in expect:
        checks.append(("no_match", (len(response.games) == 0) == expect["no_match"]))
    return checks


class TestConversation:
    """Scripted conversations replayed through graph.reply(), one session per case; after each
    turn the checkpointed state is read back (graph.state) — the per-turn 'spying' that turns
    strategy, filters and analysis into recordable trajectory data."""

    @pytest.mark.parametrize("case", CASES, ids=IDS)
    def test_case(self, graph, case, record_conversation, llm_usage):
        session = f"eval-{case['id']}"
        usage_before = llm_usage.snapshot()
        trajectory: list[dict] = []
        turn_failures: list[str] = []
        n_turn_checks = 0
        recommended: list[list[int]] = []
        strategies: list[str] = []
        fallback_turns = 0

        for t, turn in enumerate(case["turns"], start=1):
            response = graph.reply(turn["message"], choices=turn.get("choices") or [],
                                   session_id=session)
            state = graph.state(session)
            strategy = state.get("strategy")
            fallback = _is_fallback(response, state.get("hits") or [])

            recommended.append([g.id_product for g in response.games])
            strategies.append(strategy)
            fallback_turns += int(fallback)

            checks = _turn_checks(turn.get("expect") or {}, strategy, response)
            n_turn_checks += len(checks)
            turn_failures += [f"turn{t}:{name}" for name, ok in checks if not ok]

            trajectory.append({
                "turn": t,
                "user": turn["message"],
                "choices": turn.get("choices") or [],
                "strategy": strategy,
                "enthusiasm": state.get("enthusiasm"),
                "decisiveness": state.get("decisiveness"),
                "expertise": state.get("expertise_level"),
                "escalate": bool(state.get("escalate")),
                "fallback": fallback,
                # piloted arm only: this turn's searches {query, filters, n_hits} — the
                # intent reformulations and the retry path, readable in the run file.
                "searches": state.get("turn_searches"),
                "game_ids": [g.id_product for g in response.games],
                "games": [g.name for g in response.games],
                "bot": response.message,
            })

        final = case.get("final") or {}
        converged = turns_to = by_turn = None
        if final.get("accept_ids"):
            by_turn = final.get("by_turn") or len(case["turns"])
            accepted = set(final["accept_ids"])
            turns_to = next((i + 1 for i, ids in enumerate(recommended[:by_turn])
                             if accepted & set(ids)), None)
            converged = turns_to is not None

        # The final-filters oracle needs an engine that accumulates a session filter spec; a
        # black-box agent reports filters_spec=None (it re-derives constraints per turn via the
        # tool, carrying no cross-turn spec), so the oracle is out of scope for it — like
        # strategy_in for an engine with no router.
        state_filters = graph.state(session).get("filters_spec")
        final_filters = state_filters or {}
        filters_ok = None
        if final.get("filters") and state_filters is not None:
            filters_ok = all(final_filters.get(k) == v for k, v in final["filters"].items())

        proposal_ok = None
        if final.get("proposal_by_turn") and any(s is not None for s in strategies):
            proposal_ok = any(s in _PROPOSAL
                              for s in strategies[:final["proposal_by_turn"]])

        usage = llm_usage.delta_since(usage_before)
        record_conversation({
            "case": case["id"],
            "n_turns": len(case["turns"]),
            "n_turn_checks": n_turn_checks,
            "turn_failures": turn_failures,
            "converged": converged,
            "turns_to_converge": turns_to,
            "by_turn": by_turn,
            "filters_ok": filters_ok,
            "proposal_ok": proposal_ok,
            "fallback_turns": fallback_turns,
            "llm_calls": usage["llm_calls"],
            "tokens_in": usage["tokens_in"],
            "tokens_out": usage["tokens_out"],
            "trajectory": trajectory,
            "final_filters": final_filters,
            "expected": final,
            "note": case["note"],
        })
