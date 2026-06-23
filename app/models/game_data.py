import re
from typing import Optional

from pydantic import BaseModel

# The catalog's certain-data signal for cooperative play. We match the Italian stem
# 'cooperativ' (covers cooperativo/-a/-i/-e) on a word boundary — so the retailer brand
# abbrev "Coop" never counts — and we reject an explicit negation ("non cooperativo"),
# which the old naive substring test read as a false positive.
_COOP_STEM = re.compile(r"\bcooperativ", re.IGNORECASE)
_COOP_NEGATED = re.compile(r"\bnon[\s-]+cooperativ", re.IGNORECASE)


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
    # Tri-state on purpose: True = cooperative, False = competitive, None = UNKNOWN. The value is
    # an LLM inference over the description (CuratorEnricher), with an explicit catalog tag as the
    # only deterministic shortcut. UNKNOWN never narrows a search — a missing signal proves
    # nothing about the mode (SEL-142).
    cooperative: Optional[bool] = None

    # context / presentation
    categoria: Optional[str] = None
    marca: Optional[str] = None
    image: Optional[str] = None

    def mentions_cooperative(self) -> bool:
        """Whether the CERTAIN data (catalog tags + category) explicitly names cooperative play.
        A reliable POSITIVE shortcut only — its absence proves nothing, so it never yields False.

        Checked per field so an explicit negation in one tag ("non cooperativo") cannot poison
        a clean positive in another, and so "Coop" (a retailer brand) never trips the match."""
        return any(_COOP_STEM.search(s) and not _COOP_NEGATED.search(s)
                   for s in [self.categoria or "", *self.tags])
