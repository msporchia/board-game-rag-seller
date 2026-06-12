from typing import Annotated, TypedDict

from app.chat.models.response import ChatResponse
from app.models.game_hit import GameHit

HISTORY_MAX = 12  # rolling window of history entries kept in state (≈ 6 exchanges)


def add_history(left: list | None, right: list | None) -> list:
    """History reducer: append new entries, keep a rolling window."""
    return ((left or []) + (right or []))[-HISTORY_MAX:]


def merge_filters(left: dict | None, right: dict | None) -> dict:
    """Filters reducer: per-field merge — the latest click on a dimension wins."""
    return {**(left or {}), **(right or {})}


class ChatState(TypedDict, total=False):
    """The conversation state LangGraph checkpoints per session.

    Channels without a reducer are last-value (each turn's input overwrites them); `history`
    and `filters_spec` have reducers so nodes contribute fragments and the runtime accumulates.
    `filters_spec` is kept as the plain `SearchFilters.from_dict` spec (JSON-friendly for the
    checkpointer); it becomes a real SearchFilters only at retrieval time.
    """

    # per-turn inputs
    message: str
    choices: list[str]
    k: int

    # rolling conversation memory
    history: Annotated[list[str], add_history]      # "utente: ..." / "bot: ..." lines
    filters_spec: Annotated[dict, merge_filters]    # accumulated SearchFilters spec

    # analyze output (user-analysis dimensions + escalation contract, docs/note.md)
    enthusiasm: str
    decisiveness: str
    expertise_level: str
    reply_style: str
    escalate: bool
    escalation_reason: str
    confidence: float

    # routing
    strategy: str
    turns_without_proposal: int

    # retrieval / generation
    hits: list[GameHit]              # the games currently "on the table"
    last_recommended_ids: list[int]  # ids featured in the last reply
    response: ChatResponse           # this turn's output

    # piloted engine (arm B, app/chat/piloted.py) — per-turn scratch, reset by its intent
    # node every turn; the pipeline graph never reads or writes these channels.
    intent_query: str        # the model's reformulated search query (never the user verbatim)
    proposed_spec: dict      # model-proposed constraints (clicks override them per dimension)
    searches_used: int       # searches spent this turn (budget: MAX_SEARCHES_PER_TURN)
    gave_up: bool            # the retry step chose the honest no-match
    turn_searches: list[dict]  # this turn's searches {query, filters, n_hits, hit_ids} —
                               # what reached the table vs what the pitch picked (eval/debug)
