"""AssumeAdvanced — a shortcut policy: treat the customer as an advanced hobbyist this turn.

Uses the `force_expertise` shortcut (no stage to wrap): the pipeline graph's analyze node and
the engines' generate step feed the level into the persona block of the prompt.
"""

from app.chat.policies.policy import Policy


class AssumeAdvanced(Policy):
    name = "assume_advanced"
    description = "Assume an advanced expertise level for this turn (precise terminology)."

    def force_expertise(self, current: str | None) -> str:
        return "advanced"
