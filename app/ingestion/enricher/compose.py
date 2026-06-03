"""RuleComposeEnricher: DETERMINISTIC compose → writes `game.embed_text`.

Note: the composed text is intentionally in Italian — it is the embedded document for an
Italian-language catalog, i.e. system output, not source comments.
"""

from app.ingestion.enricher.base import Enricher
from app.models import GameData, GameDoc


class RuleComposeEnricher(Enricher):
    """Turns the `enriched` fields into natural sentences and writes `embed_text`.
    Baseline to beat; in production it is replaced by `CuratorEnricher`."""

    MAX_DESCRIPTION_CHARS = 1800

    def enrich(self, game: GameDoc) -> GameDoc:
        e = game.enriched
        blocks = [
            e.name,
            self._players(e),
            self._duration(e),
            self._complexity(e),
            self._tags(e),
            self._meta(e),
            self._description(e),
        ]
        text = "\n".join(b for b in blocks if b)
        return game.model_copy(update={"embed_text": text})

    def _players(self, e: GameData) -> str:
        if not e.players:
            return ""
        lo, hi = min(e.players), max(e.players)
        base = f"Si gioca in {lo} giocatori." if lo == hi else f"Si gioca da {lo} a {hi} giocatori."
        notes = []
        if 1 in e.players:
            notes.append("giocabile in solitario")
        if hi == 2:
            notes.append("ottimo in due")
        elif lo >= 4:
            notes.append("pensato per gruppi numerosi")
        elif hi >= 5:
            notes.append("adatto anche a gruppi numerosi e serate tra amici")
        if notes:
            base += " " + "; ".join(notes) + "."
        return base

    def _duration(self, e: GameData) -> str:
        d = e.duration_min
        if not d:
            return ""
        if d <= 30:
            q = "partita breve e veloce"
        elif d <= 60:
            q = "durata media, circa un'ora"
        elif d <= 120:
            q = "partita medio-lunga"
        else:
            q = "partita lunga e impegnativa"
        return f"Una partita dura circa {d} minuti ({q})."

    def _complexity(self, e: GameData) -> str:
        if not e.complexity:
            return ""
        hint = ""
        if e.complexity_level is not None:
            if e.complexity_level <= 2:
                hint = " Adatto a principianti e famiglie."
            elif e.complexity_level == 3:
                hint = " Difficoltà intermedia."
            else:
                hint = " Per giocatori esperti."
        return f"Complessità: {e.complexity}.{hint}"

    def _tags(self, e: GameData) -> str:
        return "Meccaniche e temi: " + ", ".join(e.tags) + "." if e.tags else ""

    def _meta(self, e: GameData) -> str:
        parts = []
        if e.categoria:
            parts.append(f"Categoria: {e.categoria}.")
        if e.autori:
            parts.append(f"Autore: {e.autori}.")
        if e.marca:
            parts.append(f"Editore: {e.marca}.")
        if e.year:
            parts.append(f"Anno di pubblicazione: {e.year}.")
        if e.is_expansion:
            parts.append("È un'espansione (richiede il gioco base).")
        return " ".join(parts)

    def _description(self, e: GameData) -> str:
        return e.description[: self.MAX_DESCRIPTION_CHARS] if e.description else ""
