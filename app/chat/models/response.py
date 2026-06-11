from pydantic import BaseModel

from app.models.game_hit import GameHit


class ChatResponse(BaseModel):
    message: str
    games: list[GameHit] = []
    quick_replies: list[str] = []
