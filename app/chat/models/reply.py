from pydantic import BaseModel, Field

from app.chat.models.recommendation import ChatRecommendation


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
