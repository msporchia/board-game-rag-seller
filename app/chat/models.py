"""Chat schemas — the `/chat` contract (see docs/chat.md).

Three shapes, deliberately separated:
- ChatRequest: what the frontend sends (one user turn, stateless in Phase 4).
- ChatReply: the STRUCTURED output the LLM is constrained to produce. It references the
  recommended games by `id` only — never by free text — so we can validate them against the
  retrieved set (anti-hallucination: the model may not invent a game that was not retrieved).
- ChatResponse: what the endpoint returns. The validated `recommended_ids` are hydrated back
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


class ChatReply(BaseModel):
    """The LLM's constrained output. Games are referenced by id, validated downstream."""

    message: str = Field(..., description="short Italian salesperson pitch over the shown games")
    recommended_ids: list[int] = Field(
        default=[], description="ids of the shown games to feature (subset of the retrieved set)"
    )
    quick_replies: list[str] = Field(
        default=[], description="2-3 next-step refinements, e.g. 'Solo cooperativi', 'Max 1 ora'"
    )


class ChatResponse(BaseModel):
    message: str
    games: list[GameHit] = []
    quick_replies: list[str] = []
