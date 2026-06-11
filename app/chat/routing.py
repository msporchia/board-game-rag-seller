from app.chat.models.analysis import TurnAnalysis
from app.chat.models.strategy import Strategy

# docs/note.md: "after max 3-4 exchanges without a concrete proposal → force QUICK MATCH".
FORCE_QUICK_MATCH_AFTER = 3

# How many games each strategy puts on the table (GUIDED: "massimo 1-2 scelte chiare";
# QUICK_MATCH: "3-4 giochi concreti").
STRATEGY_K = {
    Strategy.GUIDED: 2,
    Strategy.EXPLANATORY: 3,
    Strategy.DISCOVERY: 5,
    Strategy.QUICK_MATCH: 4,
}


def pick_strategy(analysis: TurnAnalysis, turns_without_proposal: int) -> Strategy:
    """The strategy transition rules from docs/note.md, as deterministic code.

    Order matters — first match wins:
      1. >= FORCE_QUICK_MATCH_AFTER exchanges without a concrete proposal → forced QUICK_MATCH.
      2. Decided user → QUICK_MATCH ("vai velocemente a proporre quando l'utente è deciso").
      3. High enthusiasm → DISCOVERY, or EXPLANATORY for beginners (they need the mechanics
         explained before free-form exploration lands).
      4. Low enthusiasm or short replies → concrete and simple: QUICK_MATCH if the user already
         shows some decisiveness, otherwise GUIDED.
      5. Default → GUIDED (the safe stance for an undecided, middle-ground user).
    """
    if turns_without_proposal >= FORCE_QUICK_MATCH_AFTER:
        return Strategy.QUICK_MATCH
    if analysis.decisiveness == "decided":
        return Strategy.QUICK_MATCH
    if analysis.enthusiasm == "high":
        return Strategy.EXPLANATORY if analysis.expertise_level == "beginner" else Strategy.DISCOVERY
    if analysis.enthusiasm == "low" or analysis.reply_style == "short":
        return Strategy.QUICK_MATCH if analysis.decisiveness == "moderate" else Strategy.GUIDED
    return Strategy.GUIDED
