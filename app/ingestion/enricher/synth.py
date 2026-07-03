"""SynthEnricher: unified LLM synthesis → rewrites `enriched.description`.

The missing link of the pipeline. The Curator (step 1) gathered facts into `game.extracted`
and the Web step (step 2) appended verified facts to the description, but until now NONE of
that reached the embedded text: Compose builds `embed_text` only from the `enriched` fields.
Synth fuses ALL the available material into one dense, search-friendly description, so the
signal that steps 1-2 worked to gather actually enters `embed_text`.

Design (see docs/enrichment/03-synth.md):
  - Division of labor with Compose: the STRUCTURED facts (players, duration, complexity, year)
    are owned by the deterministic Compose, straight from the fields — so Synth must NOT restate
    them (that would duplicate them in the embedded text). Synth owns the DESCRIPTIVE prose:
    setting/theme, genre, audience, what the game is about, plus descriptive facts recovered from
    text/web that have no structured field (e.g. "ambientato in Toscana").
  - Input = `game.extracted` (Curator) + the current description (which already carries the Web
    facts) + multi-source `source_descriptions`; the certain data is passed as CONTEXT only
    (don't contradict it), not to be restated.
  - Output = `enriched.description` rewritten as a descriptive synthesis (short, dense).
  - REWRITE, don't compress: keep theme/setting/mechanic words (the trim/v1 lesson — blind
    cutting loses recall), weave in the descriptive facts, drop only marketing noise.
  - Fuse, never invent: only facts present in the material; the step adds structure, not claims.

Note: the prompt is intentionally in Italian — it drives an Italian-language LLM over an
Italian catalog (system behavior), like the Curator and Web prompts.
"""

from langchain_ollama import ChatOllama

from app.config import settings
from app.core.logging import get_logger
from app.core.tracing.callbacks import get_trace_callbacks
from app.ingestion.enricher import prompts
from app.ingestion.enricher.enricher import Enricher
from app.models.game_data import GameData
from app.models.game_doc import GameDoc

# Synthesis budget (SEL-144): ~1600 chars sits at the measured semantic sweet spot of the
# embedder (docs/experiments.md rows 5-8) — v1's 700 normalized BELOW the optimum and lost
# recall; raw text beyond ~2-2.5k dilutes the centroid even on bge-m3.
_MAX_CHARS = 1600

logger = get_logger(__name__)


class SynthEnricher(Enricher):
    def __init__(self, model: str | None = None, base_url: str | None = None,
                 max_chars: int = _MAX_CHARS):
        self.model = model or settings.llm_model
        self.max_chars = max_chars
        # plain prose output (not JSON), deterministic
        self._llm = ChatOllama(
            model=self.model, base_url=base_url or settings.ollama_url, temperature=0,
            callbacks=get_trace_callbacks("synth"), tags=["synth"],
        )

    def enrich(self, game: GameDoc) -> GameDoc:
        material = self._material(game)
        if not material.strip():
            return game  # nothing to synthesize from
        try:
            text = (self._llm.invoke(self._prompt(game.original.name, material)).content or "").strip()
        except Exception:  # noqa: BLE001  LLM/network failure → keep the existing description
            logger.warning("synth_llm_failed", game=game.id_product,
                           fallback="keep_existing_description", exc_info=True)
            return game
        if not text:
            return game
        if len(text) > self.max_chars:  # safety cap (the prompt asks for short, this enforces it)
            text = text[: self.max_chars].rsplit(" ", 1)[0].strip()
        logger.info("synth_description_rewritten", game=game.id_product,
                    chars_before=len(game.enriched.description or ""), chars_after=len(text))
        return game.with_enriched(description=text)

    # ---- material assembly ----------------------------------------------------

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

    # ---- prompt ---------------------------------------------------------------

    def _prompt(self, name: str, material: str) -> str:
        return prompts.SYNTH_DESCRIPTION.format(
            name=name, min_words=self.max_chars // 5, max_words=self.max_chars // 4,
            material=material)
