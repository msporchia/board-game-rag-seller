from pydantic import BaseModel, Field


class ChatRecommendation(BaseModel):
    """One recommended game: the pitch is bound to the id it sells (coherence by construction)."""

    id: int = Field(..., description="id of the game, exactly as shown in the retrieved list")
    pitch: str = Field(..., description="1-2 Italian sentences selling THIS game, naming it")
