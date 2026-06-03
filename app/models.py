"""Domain Pydantic schemas.

- GameData: flat shape of a game (the DTO fields). Used for both `original` and `enriched`.
- GameDoc: working record = original (hard-truth, immutable by convention) + enriched
  (working copy that the pipeline steps fill/transform) + embed_text (text built by a
  compose step). Keeping `original` means we never lose the source and can verify the
  hard-truth.
- GameHit: a search result (game payload + score).

See docs/pipeline-dati.md.
"""

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


class GameDoc(BaseModel):
    original: GameData                  # hard-truth, immutable by convention
    enriched: GameData                  # working copy, filled/transformed by the steps
    embed_text: Optional[str] = None    # text to embed, produced by a compose step
    missing_info: list[str] = []        # requested info still missing (for the Web step)
    extracted: dict = {}                # info extracted from the description/web (curator/web → synth)

    @classmethod
    def from_dto(cls, dto: dict) -> "GameDoc":
        """Build the record from the API DTO: enriched starts as a copy of original."""
        data = GameData(**dto)
        return cls(original=data, enriched=data.model_copy(deep=True))

    @property
    def id_product(self) -> int:
        return self.original.id_product

    @property
    def content_hash(self) -> Optional[str]:
        return self.original.content_hash


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
    categoria: Optional[str] = None
    marca: Optional[str] = None
    image: Optional[str] = None
