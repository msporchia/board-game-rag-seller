from typing import Optional

from pydantic import BaseModel


class GameHit(BaseModel):
    """A game returned by a search, with its similarity score."""

    score: float
    id_product: int
    name: str
    players: list[int] = []
    players_display: Optional[str] = None
    duration_min: Optional[int] = None
    complexity: Optional[str] = None
    year: Optional[int] = None
    internal_rating: Optional[float] = None
    tags: list[str] = []
    cooperative: Optional[bool] = None
    categoria: Optional[str] = None
    marca: Optional[str] = None
    image: Optional[str] = None
