"""Strategy routing — the deterministic transition rules from docs/note.md.

Purpose: lock every rule of `pick_strategy` (pure function, no LLM involved). The forced
QUICK_MATCH through the real graph lives in `test_forced_quick_match.py`.
"""

import pytest

pytest.importorskip("langgraph")

from app.chat.routing import FORCE_QUICK_MATCH_AFTER, pick_strategy  # noqa: E402
from app.chat.models.analysis import TurnAnalysis  # noqa: E402
from app.chat.models.strategy import Strategy  # noqa: E402


def analysis(**overrides) -> TurnAnalysis:
    base = {"enthusiasm": "medium", "decisiveness": "undecided", "expertise_level": "intermediate",
            "reply_style": "long"}
    base.update(overrides)
    return TurnAnalysis(**base)


class TestTransitionRules:
    def test_decided_user_goes_quick_match(self):
        assert pick_strategy(analysis(decisiveness="decided"), 0) is Strategy.QUICK_MATCH

    def test_high_enthusiasm_beginner_gets_explanatory(self):
        a = analysis(enthusiasm="high", expertise_level="beginner")
        assert pick_strategy(a, 0) is Strategy.EXPLANATORY

    @pytest.mark.parametrize("level", ["intermediate", "advanced"])
    def test_high_enthusiasm_non_beginner_gets_discovery(self, level):
        a = analysis(enthusiasm="high", expertise_level=level)
        assert pick_strategy(a, 0) is Strategy.DISCOVERY

    def test_low_enthusiasm_undecided_gets_guided(self):
        assert pick_strategy(analysis(enthusiasm="low"), 0) is Strategy.GUIDED

    def test_short_replies_undecided_gets_guided(self):
        assert pick_strategy(analysis(reply_style="short"), 0) is Strategy.GUIDED

    def test_low_enthusiasm_but_moderate_decisiveness_gets_quick_match(self):
        # note.md: "enthusiasm low or short replies → GUIDED or QUICK MATCH"; some decisiveness
        # tips it toward concrete proposals.
        a = analysis(enthusiasm="low", decisiveness="moderate")
        assert pick_strategy(a, 0) is Strategy.QUICK_MATCH

    def test_middle_ground_defaults_to_guided(self):
        assert pick_strategy(analysis(), 0) is Strategy.GUIDED

    def test_stalled_conversation_forces_quick_match(self):
        # The forced rule wins over everything — even a high-enthusiasm DISCOVERY candidate.
        a = analysis(enthusiasm="high", expertise_level="advanced")
        assert pick_strategy(a, FORCE_QUICK_MATCH_AFTER) is Strategy.QUICK_MATCH
