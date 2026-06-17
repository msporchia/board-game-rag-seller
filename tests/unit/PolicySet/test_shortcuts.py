"""PolicySet.force_expertise/force_strategy — the shortcuts (docs/idee.md §O).

Purpose: the shortcuts fold over the policies in order, last non-None winning, and pass the
current value through unchanged when no policy sets them.
"""

from app.chat.models.strategy import Strategy
from app.chat.policies.policy_set import PolicySet


class TestShortcuts:
    def test_force_strategy_overrides_then_passes_through(self):
        forced = PolicySet.from_names(["force_quick_match"])
        assert forced.force_strategy(Strategy.GUIDED) is Strategy.QUICK_MATCH
        assert PolicySet([]).force_strategy(Strategy.GUIDED) is Strategy.GUIDED

    def test_force_expertise_overrides_then_passes_through(self):
        assert PolicySet.from_names(["assume_advanced"]).force_expertise("beginner") == "advanced"
        assert PolicySet([]).force_expertise("beginner") == "beginner"
