"""EnrichmentHarness — the single real INGEST the three phases observe.

The expensive work (real Curator/Web/Synth + embeddings) is paid ONCE here; the phase tests read
the same `RunResult`. Everything on throwaway stores (a tmp SQLite + two tmp Qdrant collections).

What it builds:
  - full targets : the oracle games through the real production pipeline
                   (Curator → Web → Synth → Compose), with the web pinned by the Rails;
  - base targets : the same games through the deterministic compose only ("before enrichment"
                   reference);
  - distractors  : every OTHER corpus game through the cheap compose, so retrieval happens against
                   a realistic ~50-game corpus (3 games alone would make any query trivial).

  - collection_full = distractors(rule) + targets(full)
  - collection_base = distractors(rule) + targets(rule)

Comparing a target's rank/keywords across the two collections is how we measure that the
enrichment made the game "richer and better placed".

The Rails are engaged for the WHOLE full ingest: any unexpected network call raises
OutOfRailsError and fails the ingest loudly.
"""

from dataclasses import dataclass, field

from app.core.enrichment_store import EnrichmentStore
from app.core.vector_store import GameVectorStore
from app.ingestion.enricher import (
    CuratorEnricher,
    EnrichmentPipeline,
    RuleComposeEnricher,
    SynthEnricher,
    WebEnricher,
)
from app.ingestion.serializer import DocumentSerializer
from app.models import GameDoc
from app.rag.retriever import GameRetriever
from tests.e2e.enrichment.cases import GameCase, load_cases, load_corpus
from tests.e2e.enrichment.rails import Rails


@dataclass
class RunResult:
    """Everything the phase tests (and the Scorecard) read from the single ingest."""

    cases: list[GameCase]
    store: EnrichmentStore                       # durable record (full pipeline)
    full_docs: dict[int, GameDoc]                # id_product → enriched GameDoc (full)
    base_embed: dict[int, str]                   # id_product → baseline embed_text (rule)
    retriever_full: GameRetriever
    retriever_base: GameRetriever
    served_queries: list[str] = field(default_factory=list)  # web queries actually issued
    _stores: list = field(default_factory=list)              # for teardown

    def case(self, id_product: int) -> GameCase:
        return next(c for c in self.cases if c.id_product == id_product)

    def close(self) -> None:
        for s in self._stores:
            try:
                s.client.delete_collection(s.collection_name)
            except Exception:
                pass
        try:
            self.store.close()
        except Exception:
            pass


class EnrichmentHarness:
    """Builds the throwaway stores and runs the full/base ingest under the Rails. `run()` is
    idempotent: it recreates the collections from scratch (`recreate=True`)."""

    def __init__(self, db_path: str, collection_full: str, collection_base: str,
                 cases: list[GameCase] | None = None):
        self.db_path = db_path
        self.collection_full = collection_full
        self.collection_base = collection_base
        self.cases = cases if cases is not None else load_cases()
        self.serializer = DocumentSerializer()

    @staticmethod
    def _rule_embed(dto: dict) -> GameDoc:
        """Baseline: the raw DTO through the deterministic compose only (no LLM, no web)."""
        return RuleComposeEnricher().enrich(GameDoc.from_dto(dto))

    def _pipeline(self, rails: Rails, store: EnrichmentStore) -> EnrichmentPipeline:
        return EnrichmentPipeline([
            CuratorEnricher(),
            # max_sources=2: two verified sources are enough to exercise the Web (ranking →
            # fetch → quoted extraction → provenance) while keeping the e2e tractable on a
            # CPU-only Ollama (each judge_extract is an LLM call over a long page).
            WebEnricher(search=rails.search, store=store, max_sources=2),
            SynthEnricher(),
            RuleComposeEnricher(),
        ])

    def run(self) -> RunResult:
        corpus = load_corpus()
        target_ids = {c.id_product for c in self.cases}

        rails = Rails(self.cases)
        store = EnrichmentStore(path=self.db_path)
        rails.seed(store)   # page cache pre-loaded → WebEnricher._fetch never hits the network

        pipeline = self._pipeline(rails, store)

        # --- full enrichment of the targets, ON THE RAILS --------------------------------------
        full_docs: dict[int, GameDoc] = {}
        base_embed: dict[int, str] = {}
        with rails.engaged():
            for c in self.cases:
                doc = pipeline.run(c.doc())   # real Curator→Web→Synth→Compose (on the stripped DTO)
                store.save_game(doc)
                full_docs[c.id_product] = doc
                # baseline = SAME (stripped) input, deterministic compose → fair comparison
                base_embed[c.id_product] = self._rule_embed(c.ingest_dto()).embed_text or ""

        ser = self.serializer

        # --- distractors (cheap compose) -------------------------------------------------------
        distractors = [self._rule_embed(dto) for idp, dto in corpus.items() if idp not in target_ids]
        dist_docs = [ser.to_document(g) for g in distractors]
        dist_ids = [GameVectorStore.point_id(g.id_product) for g in distractors]

        # --- two collections: full-targets vs base-targets, same distractors -------------------
        target_ids_ordered = [GameVectorStore.point_id(c.id_product) for c in self.cases]

        vs_full = GameVectorStore(collection_name=self.collection_full)
        full_target_docs = [ser.to_document(full_docs[c.id_product]) for c in self.cases]
        vs_full.index(dist_docs + full_target_docs, ids=dist_ids + target_ids_ordered, recreate=True)

        vs_base = GameVectorStore(collection_name=self.collection_base)
        base_target_docs = [ser.to_document(self._rule_embed(c.ingest_dto())) for c in self.cases]
        vs_base.index(dist_docs + base_target_docs, ids=dist_ids + target_ids_ordered, recreate=True)

        return RunResult(
            cases=self.cases,
            store=store,
            full_docs=full_docs,
            base_embed=base_embed,
            retriever_full=GameRetriever(store=vs_full),
            retriever_base=GameRetriever(store=vs_base),
            served_queries=rails.served,
            _stores=[vs_full, vs_base],
        )
