"""TrimEnricher: shortens the description (rough baseline)."""

import re

from app.ingestion.enricher.enricher import Enricher
from app.models.game_doc import GameDoc

_SENTENCE = re.compile(r"(?<=[.!?])\s+")


class TrimEnricher(Enricher):
    """FAILSAFE: safety cap on description length (default ~1000 chars).

    It is NOT a quality tool: it is position-blind (useful info may sit at the end) and
    aggressive cutting HURTS recall (experiment at 350, docs/valutazione.md §6). It serves as
    a guard UPSTREAM of the LLM steps: if a game has a pathologically long description, it
    reduces it to the first sentences within `max_chars` to CONTAIN costs (tokens to the LLM)
    and avoid degenerate output. High threshold → only fires on outliers. Sensible compression
    stays semantic (`CuratorEnricher`). `original.description` always stays intact.
    """

    def __init__(self, max_chars: int = 1000):
        self.max_chars = max_chars

    def enrich(self, game: GameDoc) -> GameDoc:
        desc = game.enriched.description or ""
        if len(desc) <= self.max_chars:  # guard
            return game
        kept, total = [], 0
        for sentence in _SENTENCE.split(desc):
            if kept and total + len(sentence) > self.max_chars:
                break
            kept.append(sentence)
            total += len(sentence) + 1
        return game.with_enriched(description=" ".join(kept).strip())
