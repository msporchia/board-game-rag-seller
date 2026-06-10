"""Chat schemas — the `/chat` contract (see docs/chat.md).

Three shapes, deliberately separated:
- ChatRequest: what the frontend sends (one user turn, stateless in Phase 4).
- ChatReply: the STRUCTURED output the LLM is constrained to produce. Each pitch is bound to
  its game `id` locally (one {id, pitch} pair per recommendation) so prose and cards cannot
  diverge: the customer-facing message is assembled in code from the pitches whose ids survive
  validation against the retrieved set (anti-hallucination: the model may not invent a game
  that was not retrieved — and an invented id loses its pitch too).
- ChatResponse: what the endpoint returns. The validated recommendation ids are hydrated back
  into the full `GameHit` objects the frontend needs to render cards.
- TurnAnalysis / Strategy: Phase 5 — the analyze node's structured output (the user-analysis
  dimensions + the escalation contract from docs/note.md) and the four selling strategies the
  deterministic router picks from.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.models import GameHit


class ChatRequest(BaseModel):
    message: str = Field(..., description="the user's free-text turn")
    # Quick-reply clicks. Phase 4 (stateless) appends them to the retrieval query; Phase 5
    # (with `session_id`) parses them into real hybrid-search filters merged into the session.
    choices: list[str] = []
    k: int = Field(5, ge=1, le=20)
    # Present → stateful Phase 5 path (LangGraph with session memory, keyed by this id).
    # Absent → the original stateless Phase 4 behavior, unchanged.
    session_id: str | None = None


class Strategy(str, Enum):
    """The four selling strategies (docs/note.md). Picked by deterministic code, not an LLM."""

    GUIDED = "GUIDED"            # undecided/beginner: 1-2 clear options + one simple question
    EXPLANATORY = "EXPLANATORY"  # curious: explain mechanics with plain language and analogies
    DISCOVERY = "DISCOVERY"      # enthusiast: free-form, propose creatively
    QUICK_MATCH = "QUICK_MATCH"  # decided (or stalling conversation): 3-4 concrete games, now


class TurnAnalysis(BaseModel):
    """Structured output of the analyze node: one LLM call per turn, reading the user.

    The first four fields are the user-analysis dimensions from docs/note.md; the last three are
    the model-tiering escalation contract (the analyzer proposes, deterministic code and the
    generate step act on it). Defaults are the safe middle ground, also used when the analyzer
    LLM fails — the conversation must never 500 because the analysis did.
    """

    enthusiasm: Literal["low", "medium", "high"] = "medium"
    decisiveness: Literal["undecided", "moderate", "decided"] = "undecided"
    expertise_level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    reply_style: Literal["short", "long"] = "short"

    # Escalation contract (docs/note.md "Model tiering"): when True, the generate step switches
    # to the strong model (settings.llm_model_strong). Reason and confidence are logged.
    escalate: bool = False
    escalation_reason: str = ""
    confidence: float = Field(0.5, ge=0.0, le=1.0)


class ChatRecommendation(BaseModel):
    """One recommended game: the pitch is bound to the id it sells (coherence by construction)."""

    id: int = Field(..., description="id of the game, exactly as shown in the retrieved list")
    pitch: str = Field(..., description="1-2 Italian sentences selling THIS game, naming it")


class ChatReply(BaseModel):
    """The LLM's constrained output. Games are referenced by id, validated downstream.

    The customer message is NOT a free-form field here: it is assembled in code as
    intro + the pitch of each recommendation that survives grounding validation.
    """

    intro: str = Field(
        default="", description="short Italian opening line, no game names and no ids"
    )
    recommendations: list[ChatRecommendation] = Field(
        default=[], description="2-3 picked games from the retrieved set, each with its pitch"
    )
    quick_replies: list[str] = Field(
        default=[], description="2-3 next-step refinements, e.g. 'Solo cooperativi', 'Max 1 ora'"
    )


class ChatResponse(BaseModel):
    message: str
    games: list[GameHit] = []
    quick_replies: list[str] = []
