"""WebEnricher: fills the missing info via online search (FALLBACK, hybrid).

It activates ONLY if gaps remain (`game.missing_info`, populated by the CuratorEnricher):
"online only once the local sources are exhausted". Process = mini-RAG with verification
(see docs):

    clean name → generic search → ranking by reliability (whitelist + LLM judgment)
    → fetch with UA → the LLM extracts ONLY from the text, with a verbatim quote
    → validation (is the quote really in the text?) → applies it with provenance.

HYBRID: the whitelist (`settings.web_trusted_domains`, updatable data) gives priority to
known-good domains; for UNKNOWN domains the LLM judgment decides (relevance/seriousness).
⚠️ Zero hallucinations: we keep only what is quoted and verified in the source text.

Note: the prompts and the appended output block are intentionally in Italian — system
behavior over an Italian catalog, so they are not translated.
"""

import json
from langchain_ollama import ChatOllama

from app.config import settings
from app.core.enrichment_store import EnrichmentStore
from app.core.logging import get_logger
from app.core.tracing.callbacks import get_trace_callbacks
from app.core.web_search.ddgs import DdgsSearch
from app.core.web_search.fetcher import PageFetcher
from app.core.web_search.provider import WebSearchProvider
from app.core.web_search.result import SearchResult
from app.ingestion.enricher import prompts
from app.ingestion.enricher.enricher import Enricher
from app.models.game_doc import GameDoc

# separators with which catalog names attach the marketing ("X - Gioco da Tavolo...")
_NAME_SEPARATORS = (" - ", " – ", " | ", " — ")

logger = get_logger(__name__)


class WebEnricher(Enricher):
    def __init__(self, search: WebSearchProvider | None = None, model: str | None = None,
                 base_url: str | None = None, max_sources: int | None = None,
                 store: EnrichmentStore | None = None, fetcher: PageFetcher | None = None):
        self.search_provider = search or DdgsSearch()
        self.fetcher = fetcher or PageFetcher()
        self.max_sources = max_sources or settings.web_max_sources
        self.trusted = set(settings.web_trusted_domains)
        self.blocked = set(settings.web_blocked_domains)
        self.store = store                      # optional: page cache + provenance
        self.model = model or settings.llm_model
        self._llm = ChatOllama(
            model=self.model,
            base_url=base_url or settings.ollama_url,
            format="json", temperature=0,
            callbacks=get_trace_callbacks("web"), tags=["web"],
        )

    def enrich(self, game: GameDoc) -> GameDoc:
        if not game.missing_info:
            logger.info("web_skipped", game=game.id_product, reason="no_missing_info")
            return game
        a = self.assess(game)
        facts = a["facts"]
        logger.info("web_done", game=game.id_product, sources=len(a["sources"]),
                    facts_verified=len(facts), facts_missing=len(game.missing_info))
        if not facts:
            return game  # nothing verified online → we don't touch the data

        # text block with provenance, appended to the description (enters the embed_text)
        lines = []
        for info, entries in facts.items():
            value = entries[0]["value"]               # first source (whitelist has priority)
            srcs = ", ".join(sorted({e["source"] for e in entries}))
            lines.append(f"{info}: {value} (fonte: {srcs})")
        block = "Informazioni da recensioni online — " + "; ".join(lines) + "."

        e = game.enriched
        new_desc = (e.description + "\n" + block).strip() if e.description else block
        new_missing = [m for m in game.missing_info if m not in facts]
        # Dual-write: besides the human-readable block in the description (which keeps the facts
        # in embed_text even when Synth is off), also record them in the STRUCTURED `extracted`
        # bag. That makes `extracted` the single complete fact-record (curator + web) that Synth
        # consumes and the EnrichmentStore persists. Web fills only MISSING labels, so it never
        # collides with the curator's keys; the merge is a safe progressive union.
        web_extracted = {info: entries[0]["value"] for info, entries in facts.items()}
        return game.model_copy(update={
            "enriched": e.model_copy(update={"description": new_desc}),
            "missing_info": new_missing,
            "extracted": {**game.extracted, **web_extracted},
        })

    def assess(self, game: GameDoc) -> dict:
        """Returns {"facts": {info: [{"value","source"}...]}, "sources": [url...]} (inspectable)."""
        missing = list(game.missing_info)
        if not missing:
            return {"facts": {}, "sources": []}

        results = self._ranked(self.search_provider.search(self._query(game.original.name),
                                                            settings.web_max_results))
        facts: dict[str, list[dict]] = {}
        sources: list[str] = []
        fetched = 0
        for r in results:
            if fetched >= self.max_sources or not missing:
                break
            text = self._fetch(r.url)
            if not text:
                continue
            fetched += 1
            found = self._judge_extract(game.original.name, missing, text)
            if not found:
                continue
            sources.append(r.url)
            for info, payload in found.items():
                facts.setdefault(info, []).append({"value": payload["value"], "source": r.domain})
                if self.store:                  # durable provenance (→ source scoreboard)
                    self.store.save_extraction(
                        game.id_product, info, payload["value"], payload["quote"],
                        r.url, r.domain, self.model,
                    )
        return {"facts": facts, "sources": sources}

    # ---- discovery: name → query → ranking ----

    def _query(self, name: str) -> str:
        return f"{self._clean_name(name)} gioco da tavolo recensione"

    @staticmethod
    def _clean_name(name: str) -> str:
        """Strips the marketing from the catalog name: 'Viticulture Essential - Gioco...' → 'Viticulture Essential'."""
        for sep in _NAME_SEPARATORS:
            if sep in name:
                name = name.split(sep, 1)[0]
        return name.strip()

    def _ranked(self, results: list[SearchResult]) -> list[SearchResult]:
        """Discards blocklisted domains; whitelist first (order preserved), then the unknown ones."""
        results = [r for r in results if r.domain not in self.blocked]
        trusted = [r for r in results if r.domain in self.trusted]
        others = [r for r in results if r.domain not in self.trusted]
        return trusted + others

    # ---- fetch (cached) ----

    def _fetch(self, url: str) -> str:
        """Cached fetch: if the page is already in the store it is not re-downloaded."""
        if self.store:
            cached = self.store.get_page(url)
            if cached is not None:
                return cached
        text = self.fetcher.fetch(url)
        if self.store and text:
            self.store.save_page(url, 200, text)
        return text

    # ---- judgment + extraction (a single LLM round per source) ----

    def _judge_extract(self, name: str, missing: list[str], text: str) -> dict:
        """One LLM round: judgment + quoted extraction. Keeps only the info whose quote is
        verifiable in the text (anti-hallucination). Returns {info: {"value","quote"}}.
        {} if not relevant / not serious / parse failed."""
        data = self._run_llm(name, missing, text)
        if data is None:
            return {}
        if not data.get("is_this_game") or not data.get("is_serious"):
            return {}
        norm_text = self._normalize(text)
        verified = {}
        for info, payload in (data.get("found") or {}).items():
            if info not in missing or not isinstance(payload, dict):
                continue
            value = (payload.get("value") or "").strip()
            quote = (payload.get("quote") or "").strip()
            # the quote MUST appear in the source text, otherwise it is fabricated → discard
            if value and quote and self._normalize(quote) in norm_text:
                verified[info] = {"value": value, "quote": quote}
        return verified

    def _run_llm(self, name: str, missing: list[str], text: str) -> dict | None:
        """Calls the LLM and parses the raw JSON. `None` if the output is not valid JSON.
        The eval tests use it to inspect judgment and extraction separately; the filtering
        (relevance, seriousness, verified quote) is applied by `_judge_extract`."""
        try:
            raw = self._llm.invoke(self._prompt(name, missing, text)).content
            return json.loads(raw)
        except Exception:  # noqa: BLE001  LLM/parse failure → source skipped
            logger.warning("web_judge_failed", game_name=name, exc_info=True)
            return None

    def _prompt(self, name: str, missing: list[str], text: str) -> str:
        return prompts.WEB_JUDGE_EXTRACT.format(
            name=name, aspects=", ".join(missing), text=text)

    @staticmethod
    def _normalize(s: str) -> str:
        return " ".join(s.lower().split())
