"""ConversationDriver — the per-case turn loop + oracle scoring of the ChatConversation eval.

Factored out of `test_conversation.py::TestConversation.test_case` so the exact same driver can
be reused OUTSIDE pytest by the strong-model simulation harness
(tests/eval/ChatConversation/simulation/run.py) without forking the scoring logic: the
simulation must be judged by the SAME oracle as the 8B baseline, or the comparison is not a
comparison. See `test_conversation.py`'s module docstring for the case taxonomy and the oracle
rationale, and `report.ConversationReport` for how the returned record is aggregated.
"""

from app.chat.advisor import ChatAdvisor
from app.chat.models.response import ChatResponse
from app.models.game_hit import GameHit

_PROPOSAL = {"QUICK_MATCH", "DISCOVERY"}


class ConversationDriver:
    """Replays one scripted case through `engine.reply()`, one session per case; after each turn
    the engine's own state (`engine.state(session)`) is read back — the per-turn 'spying' that
    turns strategy, filters and analysis into recordable trajectory data. `engine` is anything
    with the `reply(message, choices, k, session_id, ...) -> ChatResponse` / `state(session_id)
    -> dict` contract (ChatGraph, PilotedChat, AgenticChat — and the simulation's own instances
    of them, wired with FileExchange* LLMs instead of Ollama)."""

    def run(self, engine, case: dict, llm_usage) -> dict:
        session = f"eval-{case['id']}"
        usage_before = llm_usage.snapshot()
        trajectory: list[dict] = []
        turn_failures: list[str] = []
        n_turn_checks = 0
        recommended: list[list[int]] = []
        strategies: list[str] = []
        fallback_turns = 0

        for t, turn in enumerate(case["turns"], start=1):
            response = engine.reply(turn["message"], choices=turn.get("choices") or [],
                                    session_id=session)
            state = engine.state(session)
            strategy = state.get("strategy")
            fallback = self._is_fallback(response, state.get("hits") or [])

            recommended.append([g.id_product for g in response.games])
            strategies.append(strategy)
            fallback_turns += int(fallback)

            checks = self._turn_checks(turn.get("expect") or {}, strategy, response)
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
        state_filters = engine.state(session).get("filters_spec")
        final_filters = state_filters or {}
        filters_ok = None
        if final.get("filters") and state_filters is not None:
            filters_ok = all(final_filters.get(k) == v for k, v in final["filters"].items())

        proposal_ok = None
        if final.get("proposal_by_turn") and any(s is not None for s in strategies):
            proposal_ok = any(s in _PROPOSAL
                              for s in strategies[:final["proposal_by_turn"]])

        usage = llm_usage.delta_since(usage_before)
        return {
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
        }

    @staticmethod
    def _is_fallback(response: ChatResponse, hits: list[GameHit]) -> bool:
        """True iff `response` is byte-identical to `ChatAdvisor._fallback(hits)` (the ChatPitch
        reconstruction, over the hits the graph state had on the table this turn)."""
        return bool(hits) and (
            response.message == ChatAdvisor._plain_pitch(hits[:3])
            and response.quick_replies == []
            and [g.id_product for g in response.games] == [h.id_product for h in hits[:3]])

    @staticmethod
    def _turn_checks(expect: dict, strategy: str, response: ChatResponse) -> list[tuple[str, bool]]:
        """Evaluate the per-turn oracles a case declares; absent keys are out of scope — and so
        is `strategy_in` when the engine has no strategy router (state leaves `strategy` unset)."""
        checks = []
        if "strategy_in" in expect and strategy is not None:
            checks.append(("strategy_in", strategy in expect["strategy_in"]))
        if "min_games" in expect:
            checks.append(("min_games", len(response.games) >= expect["min_games"]))
        if "no_match" in expect:
            checks.append(("no_match", (len(response.games) == 0) == expect["no_match"]))
        return checks
