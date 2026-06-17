"""ForceQuickMatch — the strategy shortcut policy (docs/idee.md §O).

Purpose: it forces QUICK_MATCH via `force_strategy` and leaves every other seam as pass-through
(a policy touches exactly what it declares — what keeps effects isolated/testable).
"""

from app.chat.models.strategy import Strategy
from app.chat.policies.library.force_quick_match import ForceQuickMatch


class TestForceQuickMatch:
    def test_forces_quick_match_strategy(self):
        assert ForceQuickMatch().force_strategy(Strategy.GUIDED) is Strategy.QUICK_MATCH

    def test_leaves_expertise_and_stages_untouched(self):
        policy = ForceQuickMatch()
        sentinel = object()
        assert policy.force_expertise("beginner") is None
        assert policy.around_retrieve("ctx", lambda c: sentinel) is sentinel
        assert policy.around_generate("ctx", lambda c: sentinel) is sentinel
