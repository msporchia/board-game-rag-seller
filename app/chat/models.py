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
"""

from pydantic import BaseModel, Field

from app.models import GameHit


class ChatRequest(BaseModel):
    message: str = Field(..., description="the user's free-text turn")
    # Quick-reply clicks. Phase 4 (stateless) appends them to the retrieval query; Phase 5 will
    # turn them into real hybrid-search filters.
    choices: list[str] = []
    k: int = Field(5, ge=1, le=20)


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
