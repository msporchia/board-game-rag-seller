from typing import Optional

from pydantic import BaseModel

from app.models.game_data import GameData


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

    def with_enriched(self, **updates) -> "GameDoc":
        """New GameDoc with an updated `enriched` (original untouched)."""
        return self.model_copy(update={"enriched": self.enriched.model_copy(update=updates)})

    @property
    def id_product(self) -> int:
        return self.original.id_product

    @property
    def content_hash(self) -> Optional[str]:
        return self.original.content_hash
