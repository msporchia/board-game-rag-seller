from enum import Enum


class Strategy(str, Enum):
    """The four selling strategies (docs/note.md). Picked by deterministic code, not an LLM."""

    GUIDED = "GUIDED"            # undecided/beginner: 1-2 clear options + one simple question
    EXPLANATORY = "EXPLANATORY"  # curious: explain mechanics with plain language and analogies
    DISCOVERY = "DISCOVERY"      # enthusiast: free-form, propose creatively
    QUICK_MATCH = "QUICK_MATCH"  # decided (or stalling conversation): 3-4 concrete games, now
