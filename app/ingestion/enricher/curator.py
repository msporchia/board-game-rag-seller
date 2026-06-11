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
from app.core.tracing import get_trace_callbacks
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

    def _needed_labels(self, e: GameData) -> list[str]:
        """Labels to ask the LLM: descriptive (always) + structured ones missing in the DTO."""
        return list(self.DESCRIPTIVE_INFO) + [
            label for label, has in self.STRUCTURED_INFO.items() if not has(e)
        ]

    @classmethod
    def _structurally_present(cls, e: GameData) -> list[str]:
        """Structured labels ALREADY in the certain data → go straight to `presenti`, no LLM."""
        return [label for label, has in cls.STRUCTURED_INFO.items() if has(e)]

    def _certain_facts(self, e: GameData) -> str:
        f = []
        if e.players:
            f.append(f"Giocatori: {e.players_display or e.players}")
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
        return "\n".join(f) or "(nessuno)"

    def _collect_descriptions(self, game: GameDoc) -> str:
        """Gathers ALL available descriptive material, labeled by source: the main description
        PLUS all per-source `source_descriptions`. More material → the LLM fills the gaps by
        drawing on different sources. Dedupes identical texts and keeps the order (main first,
        then per source)."""
        blocks = []
        seen = set()
        main = (game.original.description or game.enriched.description or "").strip()
        if main:
            blocks.append(f"[Descrizione principale]\n{main}")
            seen.add(main)
        for entry in game.original.source_descriptions or []:
            if not isinstance(entry, dict):
                continue
            text = (entry.get("description") or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            source = (entry.get("source") or "fonte").strip() or "fonte"
            blocks.append(f"[Fonte: {source}]\n{text}")
        return "\n\n".join(blocks)

    @staticmethod
    def _prompt(labels: list[str], description: str) -> str:
        """Focused prompt: only the LABELS we need, only the DESCRIPTION.

        No CERTAIN DATA: we apply those downstream (they always win, even if the LLM said
        otherwise). The 8B's cognitive load is reduced to a minimum.
        """
        bullet = "\n".join(f"- {l}" for l in labels)
        return f"""Compito: per OGNI etichetta della LISTA estrai dalla DESCRIZIONE il
valore richiesto. Anti-invenzione: se non puoi copiare una citazione VERBATIM dalla
DESCRIZIONE che lo dimostri, scrivi "NESSUNO".

ETICHETTE da analizzare (esattamente {len(labels)}, nell'ordine):
{bullet}

Per OGNI etichetta produci un oggetto con questi campi:
- "citazione": testo VERBATIM (max 80 caratteri) copiato dalla DESCRIZIONE. DEVE essere
  copiato letteralmente — sarà verificato a valle. Stringa vuota se non c'è.
- "valore_normalizzato": valore breve e normalizzato (es. "fantasy", "mitologia greca",
  "cooperativo", "famiglie", "120 minuti", "1-4", "media"). Stringa "NESSUNO" se non si
  riesce a citare.

Regole rigide:
- Se la DESCRIZIONE non contiene esplicitamente l'informazione → "valore_normalizzato":
  "NESSUNO" e "citazione": "". NON inferire dal tono o dall'atmosfera.
- "numero giocatori" si estrae SOLO se c'è un numero/range esplicito (es. "2 a 4
  giocatori"). NON inferire dal genere o da "famiglia".
- "durata" si estrae SOLO se c'è un numero esplicito di minuti/ore. Non aggiungere range
  "verosimili".

DESCRIZIONE:
{description[:8000]}

Rispondi SOLO con JSON, una chiave per ogni etichetta della LISTA:
{{"<etichetta1>": {{"citazione":"...","valore_normalizzato":"..."}},
  "<etichetta2>": {{...}}, ...}}"""

    @staticmethod
    def _str_list(value) -> list[str]:
        return [x for x in (value or []) if isinstance(x, str)]

    @staticmethod
    def _norm(s: str) -> str:
        """Normalize for verbatim quote matching (case + whitespace)."""
        return " ".join((s or "").lower().split())

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

    def _ask_llm(self, labels: list[str], desc: str) -> dict:
        """A single LLM call over a BATCH of labels. {} on failure."""
        try:
            raw = self._llm.invoke(self._prompt(labels, desc)).content
            data = json.loads(raw)
        except Exception:  # noqa: BLE001  intentional: LLM/parse/network → batch ignored
            logger.warning("curator_llm_batch_failed", labels=labels, exc_info=True)
            return {}
        return data if isinstance(data, dict) else {}

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
        return game.model_copy(update={
            "enriched": new_enriched,
            "missing_info": a.get("mancanti", []),
            "extracted": {**game.extracted, **a.get("estratti", {})},  # progressive merge
        })
