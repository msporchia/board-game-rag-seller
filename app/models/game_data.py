from typing import Optional

from pydantic import BaseModel


class GameData(BaseModel):
    # identity
    id_product: int
    name: str
    content_hash: Optional[str] = None

    # text
    description: str = ""
    source_descriptions: list[dict] = []  # [{"source": str, "description": str}, ...] raw multi-source material
    tags: list[str] = []
    autori: Optional[str] = None

    # structured (filters)
    players: list[int] = []
    players_display: Optional[str] = None
    duration_min: Optional[int] = None
    age_min: Optional[int] = None
    complexity: Optional[str] = None
    complexity_level: Optional[int] = None
    year: Optional[int] = None
    internal_rating: Optional[float] = None
    is_expansion: bool = False

    # context / presentation
    categoria: Optional[str] = None
    marca: Optional[str] = None
    image: Optional[str] = None
