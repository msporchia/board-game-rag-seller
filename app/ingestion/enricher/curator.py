"""CuratorEnricher: focused LLM pass — classification + extraction (NO synthesis).

Narrower scope than v1: it now does ONLY two things, so as not to overload a local 8B model
(v1, with "synthesis+extraction+classification" in one call, hallucinated the presence of
missing fields and produced malformed JSON). The unified synthesis lives in `SynthEnricher`,
downstream of Web, over ALL available material (certain data + curator extractions + web
facts + multi-source source_descriptions).

Note: the prompts and taxonomy labels below are intentionally in Italian — they drive an
Italian-language LLM over an Italian catalog (system behavior), so they are not translated.
"""

import json
from langchain_ollama import ChatOllama

from app.config import settings
from app.core.logging import get_logger
from app.core.tracing.callbacks import get_trace_callbacks
from app.ingestion.enricher import prompts
from app.ingestion.enricher.enricher import Enricher
from app.models.game_data import GameData
from app.models.game_doc import GameDoc

logger = get_logger(__name__)


class CuratorEnricher(Enricher):
    """LLM pass focused on what we do NOT already know.

    Architecture (post-measurement):
      - **No CERTAIN DATA in the prompt**: the LLM reads ONLY the description. We apply the
        certain data downstream ourselves (it always wins). This halves the 8B's cognitive load.
      - **Dynamic list of info to ask**: only the `DESCRIPTIVE_INFO` (always, since they are
        not in the DTO) and the `STRUCTURED_INFO` that turn out MISSING in the DTO (in
        production, on real DTOs, these are almost always set — so in practice only 3 are asked).
      - **Optional chunking** (`max_per_call`): if the list exceeds the threshold, the LLM is
        queried over several rounds (default 4).

    `assess()` returns `{estratti, presenti, mancanti}` as a stable API for the rest of the
    pipeline. `enrich()` applies: extracted mechanics → tags (if empty), `missing_info` ←
    mancanti, `extracted` ← estratti. It does NOT touch `description` (that's `SynthEnricher`'s job).
    """

    # 3 purely DESCRIPTIVE info (do not exist in the DTO) → always asked to the LLM
    DESCRIPTIVE_INFO = ["ambientazione/tema", "genere", "a chi è adatto"]

    # 4 info that have a structured field in the DTO → we ask ONLY if the DTO lacks it
    STRUCTURED_INFO: dict = {
        "meccaniche principali": lambda e: bool(e.tags),
        "numero giocatori":      lambda e: bool(e.players),
        "durata":                lambda e: e.duration_min is not None,
        "complessità":           lambda e: bool(e.complexity),
    }

    # all 7 info the system considers (DESCRIPTIVE + STRUCTURED): the stable taxonomy used by
    # `missing_info` / `extracted` / WebEnricher / Synth.
    REQUIRED_INFO = DESCRIPTIVE_INFO + list(STRUCTURED_INFO)

    def __init__(self, model: str | None = None, base_url: str | None = None,
                 max_per_call: int = 4):
        self.model = model or settings.llm_model
        self.base_url = base_url or settings.ollama_url
        self.max_per_call = max_per_call
        self._llm = ChatOllama(
            model=self.model, base_url=self.base_url, format="json", temperature=0,
            callbacks=get_trace_callbacks("curator"), tags=["curator"],
        )

    def enrich(self, game: GameDoc) -> GameDoc:
        a = self.assess(game)
        logger.info("curator_done", game=game.id_product,
                    extracted=len(a.get("estratti", {})),
                    missing=len(a.get("mancanti", [])), missing_labels=a.get("mancanti", []))
        e = game.enriched
        # mechanics extracted from the text → tags (only if empty; certain data ALWAYS wins)
        deduced_mec = a.get("estratti", {}).get("meccaniche principali")
        new_enriched = (e.model_copy(update={"tags": deduced_mec})
                        if (not e.tags and isinstance(deduced_mec, list) and deduced_mec) else e)
        # cooperative (SEL-142): an explicit catalog tag is certain data and wins; otherwise the
        # mode is INFERRED from the description (a semantic verdict True/False/None) — not a
        # verbatim match, so a game that plays co-op without the word is still caught.
        if new_enriched.cooperative is None:
            verdict = self._cooperative_verdict(game, new_enriched)
            if verdict is not None:
                new_enriched = new_enriched.model_copy(update={"cooperative": verdict})
        return game.model_copy(update={
            "enriched": new_enriched,
            "missing_info": a.get("mancanti", []),
            "extracted": {**game.extracted, **a.get("estratti", {})},  # progressive merge
        })

    def assess(self, game: GameDoc) -> dict:
        """Raw LLM assessment. Canonical output (stable API): `estratti`, `presenti`,
        `mancanti`. Returns `{}` if NO label is needed from the LLM (impossible case, since the
        3 DESCRIPTIVE_INFO are never in the DTO) or if the call pipeline fails systematically.

        Strategy:
          1) Structured ones ALREADY in the DTO → straight to `presenti`, no LLM.
          2) Dynamic list of `needed_labels` (descriptive + missing structured).
          3) Chunking: if `len(needed) > max_per_call`, batches of `max_per_call`.
          4) Per batch: LLM call only over the DESCRIPTION; verbatim validation of the
             extracted values; a label is "present" IF the extraction is validated, otherwise
             it ends up in "mancanti".
          5) Merge of the batch outputs.
        """
        e = game.enriched
        desc = (game.original.description or e.description or "").strip()
        desc_n = self._norm(desc)

        needed = self._needed_labels(e)
        presenti = list(self._structurally_present(e))   # those in the certain data: zero LLM
        if not needed:
            return {"estratti": {}, "presenti": presenti, "mancanti": []}

        estratti: dict = {}
        for i in range(0, len(needed), self.max_per_call):
            batch = needed[i:i + self.max_per_call]
            per_label = self._ask_llm(batch, desc)
            estratti.update(self._validate_extraction(per_label, batch, desc_n))

        presenti += [l for l in needed if l in estratti]
        mancanti = [l for l in needed if l not in estratti]
        return {"estratti": estratti, "presenti": presenti, "mancanti": mancanti}

    # ---- assess internals (in call order) ----

    def _needed_labels(self, e: GameData) -> list[str]:
        """Labels to ask the LLM: descriptive (always) + structured ones missing in the DTO."""
        return list(self.DESCRIPTIVE_INFO) + [
            label for label, has in self.STRUCTURED_INFO.items() if not has(e)
        ]

    @classmethod
    def _structurally_present(cls, e: GameData) -> list[str]:
        """Structured labels ALREADY in the certain data → go straight to `presenti`, no LLM."""
        return [label for label, has in cls.STRUCTURED_INFO.items() if has(e)]

    def _cooperative_verdict(self, game: GameDoc, e: GameData) -> bool | None:
        """The `cooperative` flag: True / False / None. CERTAIN data wins (an explicit catalog
        co-op tag/category → True, no LLM); otherwise the mode is INFERRED from the description."""
        if e.mentions_cooperative():
            return True
        desc = (game.original.description or e.description or "").strip()
        return self._infer_cooperative(desc) if desc else None

    def _infer_cooperative(self, desc: str) -> bool | None:
        """LLM INFERENCE (not verbatim extraction): classify the play mode from the MEANING of
        the description. True (cooperativo) / False (competitivo) / None (incerto or failure).
        On unknown we stay None — never a guessed verdict (SEL-142)."""
        try:
            raw = self._llm.invoke(self._coop_prompt(desc)).content
            modalita = str((json.loads(raw) or {}).get("modalita", "")).strip().lower()
        except Exception:  # noqa: BLE001  LLM/parse/network failure → unknown, not a wrong verdict
            logger.warning("curator_coop_infer_failed", exc_info=True)
            return None
        if modalita == "cooperativo":
            return True
        if modalita == "competitivo":
            return False
        return None

    @staticmethod
    def _coop_prompt(desc: str) -> str:
        """Inference prompt: a reasoned classification of the play mode, not a keyword hunt."""
        return prompts.COOP_INFER.format(desc=desc[:8000])

    def _ask_llm(self, labels: list[str], desc: str) -> dict:
        """A single LLM call over a BATCH of labels. {} on failure."""
        try:
            raw = self._llm.invoke(self._prompt(labels, desc)).content
            data = json.loads(raw)
        except Exception:  # noqa: BLE001  intentional: LLM/parse/network → batch ignored
            logger.warning("curator_llm_batch_failed", labels=labels, exc_info=True)
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _prompt(labels: list[str], description: str) -> str:
        """Focused prompt: only the LABELS we need, only the DESCRIPTION.

        No CERTAIN DATA: we apply those downstream (they always win, even if the LLM said
        otherwise). The 8B's cognitive load is reduced to a minimum.
        """
        bullet = "\n".join(f"- {l}" for l in labels)
        return prompts.CURATOR_EXTRACT.format(
            count=len(labels), bullet=bullet, description=description[:8000])

    @classmethod
    def _validate_extraction(cls, per_label: dict, labels: list[str], desc_n: str) -> dict:
        """From `{label: {citazione, valore_normalizzato}}` returns the VALIDATED extractions.

        Anti-fabrication validation (same pattern as the WebEnricher): we keep only the
        extraction whose QUOTE is verbatim in the DESCRIPTION (case+whitespace insensitive).
        If the quote is not found, the extraction is discarded — the LLM made it up and it will
        fall into `mancanti` downstream. Fallback: if the LLM left `valore_normalizzato` empty
        but quotes a valid passage, we use the quote.
        """
        out: dict = {}
        for label in labels:
            info = (per_label or {}).get(label)
            if not isinstance(info, dict):
                continue
            cit_raw = (info.get("citazione") or "").strip()
            val = (info.get("valore_normalizzato") or "").strip()
            if val.upper() == "NESSUNO" or not cit_raw:
                continue
            if cls._norm(cit_raw) not in desc_n:
                continue  # fabricated quote → discarded
            extracted = val or cit_raw
            if label == "meccaniche principali":
                parts = [p.strip() for p in extracted.replace(";", ",").split(",")]
                parts = [p for p in parts if p]
                if parts:
                    out[label] = parts
            elif extracted and extracted.upper() != "NESSUNO":
                out[label] = extracted
        return out

    @staticmethod
    def _norm(s: str) -> str:
        """Normalize for verbatim quote matching (case + whitespace)."""
        return " ".join((s or "").lower().split())
