"""Ingest orchestration: source -> builder -> vector store.

Dependencies are injected (source/builder/store), so they're easy to swap in tests or to
add different sources.

    docker exec seller-api python -m app.ingestion.ingester --max-pages 2   # validation
    docker exec seller-api python -m app.ingestion.ingester                 # full catalog
"""

import argparse

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
from app.ingestion.sources import GameSource, PrestashopSource


def build_pipeline(store: EnrichmentStore | None = None) -> EnrichmentPipeline:
    """The production enrichment chain, in pipeline order (see docs/enrichment/):

        Curator (extract facts → `extracted`) → Web (fill the gaps, fallback) →
        Synth (fuse everything into `enriched.description`) → Compose (assemble `embed_text`).

    Compose is last so `embed_text` is always present. The store is injected into Web for the
    page cache and extraction provenance. Eval builds its own (experiment) pipelines instead.
    """
    return EnrichmentPipeline([
        CuratorEnricher(),
        WebEnricher(store=store),
        SynthEnricher(),
        RuleComposeEnricher(),
    ])


class Ingester:
    def __init__(self, source: GameSource | None = None,
                 serializer: DocumentSerializer | None = None,
                 store: GameVectorStore | None = None,
                 pipeline: EnrichmentPipeline | None = None,
                 enrichment_store: EnrichmentStore | None = None):
        self.source = source or PrestashopSource()
        self.serializer = serializer or DocumentSerializer()   # GameDoc → Document (thin)
        self.store = store or GameVectorStore()
        # optional: persists the curated record (system-of-record). None in test/eval.
        self.enrichment_store = enrichment_store
        # default: the full production chain (curator → web → synth → compose), with the
        # enrichment store injected into Web (page cache + provenance). Eval/tests inject
        # their own pipeline; Compose stays last so embed_text is always present.
        self.pipeline = pipeline or build_pipeline(store=self.enrichment_store)

    def run(self, recreate: bool = True, **fetch_kwargs) -> int:
        print("[1/3] Reading games from the source...", flush=True)
        games = self.source.fetch(**fetch_kwargs)
        print(f"      -> {len(games)} games", flush=True)
        if not games:
            return 0

        games = [self.pipeline.run(g) for g in games]          # data enrichment
        if self.enrichment_store:                              # persist the curated data
            for g in games:
                self.enrichment_store.save_game(g)
        documents = [self.serializer.to_document(g) for g in games]
        ids = [GameVectorStore.point_id(g.id_product) for g in games]

        print(f"[2/3] Embedding + upsert to Qdrant (recreate={recreate})...", flush=True)
        self.store.index(documents, ids=ids, recreate=recreate)

        print(f"[3/3] Done: {len(documents)} documents indexed.", flush=True)
        return len(documents)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=None, help="limit the pages (validation)")
    ap.add_argument("--no-recreate", action="store_true", help="incremental upsert instead of recreate")
    ap.add_argument("--no-store", action="store_true", help="do not persist the curated data to SQLite")
    args = ap.parse_args()
    Ingester(
        enrichment_store=None if args.no_store else EnrichmentStore(),
    ).run(recreate=not args.no_recreate, max_pages=args.max_pages)
