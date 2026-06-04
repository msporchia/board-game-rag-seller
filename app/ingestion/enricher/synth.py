"""SynthEnricher: unified LLM synthesis → rewrites `enriched.description`.

The missing link of the pipeline. The Curator (step 1) gathered facts into `game.extracted`
and the Web step (step 2) appended verified facts to the description, but until now NONE of
that reached the embedded text: Compose builds `embed_text` only from the `enriched` fields.
Synth fuses ALL the available material into one dense, search-friendly description, so the
signal that steps 1-2 worked to gather actually enters `embed_text`.

Design (see docs/enrichment/03-synth.md):
  - Input = certain data (structured fields) + `game.extracted` (Curator) + the current
    description (which already carries the Web facts) + multi-source `source_descriptions`.
  - Output = `enriched.description` rewritten as a unified synthesis (~400-600 chars).
  - REWRITE, don't compress: keep theme/setting/mechanic words (the trim/v1 lesson — blind
    cutting loses recall), weave in the canonical facts, drop only marketing noise.
  - Fuse, never invent: only facts present in the material; the step adds structure, not claims.

Note: the prompt is intentionally in Italian — it drives an Italian-language LLM over an
Italian catalog (system behavior), like the Curator and Web prompts.
"""

from langchain_ollama import ChatOllama

from app.config import settings
from app.ingestion.enricher.base import Enricher, with_enriched
from app.models import GameData, GameDoc

# Keep the synthesis short: dense facts beat long prose (less dilution of the embedding).
_MAX_CHARS = 700


class SynthEnricher(Enricher):
    def __init__(self, model: str | None = None, base_url: str | None = None,
                 max_chars: int = _MAX_CHARS):
        self.model = model or settings.llm_model
        self.max_chars = max_chars
        # plain prose output (not JSON), deterministic
        self._llm = ChatOllama(
            model=self.model, base_url=base_url or settings.ollama_url, temperature=0
        )

    # ---- material assembly ----------------------------------------------------

    def _certain_facts(self, e: GameData) -> str:
        """The structured certain data, as labeled lines. These always win."""
        f = []
        if e.players:
            lo, hi = min(e.players), max(e.players)
            f.append(f"Giocatori: {e.players_display or (lo if lo == hi else f'{lo}-{hi}')}")
        if e.duration_min:
            f.append(f"Durata: {e.duration_min} minuti")
        if e.complexity:
            f.append(f"Complessità: {e.complexity}")
        if e.tags:
            f.append(f"Meccaniche/temi: {', '.join(e.tags)}")
        if e.categoria:
            f.append(f"Categoria: {e.categoria}")
        if e.year:
            f.append(f"Anno: {e.year}")
        return "\n".join(f)

    @staticmethod
    def _extracted_facts(extracted: dict) -> str:
        """The Curator's extractions (setting, genre, audience...), as labeled lines."""
        lines = []
        for label, value in (extracted or {}).items():
            val = ", ".join(value) if isinstance(value, list) else str(value)
            if val:
                lines.append(f"{label}: {val}")
        return "\n".join(lines)

    def _material(self, game: GameDoc) -> str:
        """All the material Synth is allowed to draw from, labeled by kind."""
        e = game.enriched
        blocks = []
        certain = self._certain_facts(e)
        if certain:
            blocks.append("[DATI CERTI]\n" + certain)
        extracted = self._extracted_facts(game.extracted)
        if extracted:
            blocks.append("[INFO ESTRATTE]\n" + extracted)
        desc = (e.description or "").strip()
        if desc:
            blocks.append("[DESCRIZIONE]\n" + desc)
        return "\n\n".join(blocks)

    # ---- prompt ---------------------------------------------------------------

    def _prompt(self, name: str, material: str) -> str:
        return f"""Sei un redattore di giochi da tavolo. Riscrivi UNA descrizione unica e
concisa del gioco "{name}", fondendo TUTTO il materiale qui sotto.

Regole rigide:
- Usa SOLO fatti presenti nel materiale. NON inventare nulla (niente numeri, ambientazioni o
  meccaniche non citati). Se un'informazione non c'è, non scriverla.
- I [DATI CERTI] hanno sempre la priorità: se il testo li contraddice, vincono i dati certi.
- MANTIENI le parole-chiave di tema, ambientazione e meccaniche (es. "cooperativo", "fantasy",
  "Toscana", "piazzamento lavoratori"): servono alla ricerca. Togli solo il marketing vuoto.
- Stile: denso e fattuale, una sintesi di {self.max_chars // 5}-{self.max_chars // 4} parole
  circa. Niente elenco puntato, niente titoli: testo scorrevole.

MATERIALE:
{material}

Rispondi SOLO con la descrizione riscritta, senza preamboli."""

    # ---- API ------------------------------------------------------------------

    def enrich(self, game: GameDoc) -> GameDoc:
        material = self._material(game)
        if not material.strip():
            return game  # nothing to synthesize from
        try:
            text = (self._llm.invoke(self._prompt(game.original.name, material)).content or "").strip()
        except Exception:  # noqa: BLE001  LLM/network failure → keep the existing description
            return game
        if not text:
            return game
        if len(text) > self.max_chars:  # safety cap (the prompt asks for short, this enforces it)
            text = text[: self.max_chars].rsplit(" ", 1)[0].strip()
        return with_enriched(game, description=text)
