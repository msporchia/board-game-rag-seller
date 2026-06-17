"""AssumeAdvanced — the expertise shortcut policy (docs/idee.md §O).

Purpose: it forces the advanced level via `force_expertise` and leaves every other seam as
pass-through (a policy touches exactly what it declares — what keeps effects isolated/testable).
"""

from app.chat.models.strategy import Strategy
from app.chat.policies.library.assume_advanced import AssumeAdvanced


class TestAssumeAdvanced:
    def test_forces_advanced_expertise(self):
        assert AssumeAdvanced().force_expertise("beginner") == "advanced"

    def test_leaves_strategy_and_stages_untouched(self):
        policy = AssumeAdvanced()
        sentinel = object()
        assert policy.force_strategy(Strategy.GUIDED) is None
        assert policy.around_retrieve("ctx", lambda c: sentinel) is sentinel
        assert policy.around_generate("ctx", lambda c: sentinel) is sentinel
