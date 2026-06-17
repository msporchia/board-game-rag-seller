"""ForceQuickMatch — a shortcut policy: force the QUICK_MATCH selling strategy this turn.

Uses the `force_strategy` shortcut: the pipeline graph's route node takes this instead of the
deterministic `pick_strategy`, so the turn proposes 3-4 concrete games immediately.
"""

from app.chat.models.strategy import Strategy
from app.chat.policies.policy import Policy


class ForceQuickMatch(Policy):
    name = "force_quick_match"
    description = "Force the QUICK_MATCH strategy (propose concrete games now)."

    def force_strategy(self, current: Strategy) -> Strategy:
        return Strategy.QUICK_MATCH
