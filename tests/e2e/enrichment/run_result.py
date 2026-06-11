"""RunResult — everything the phase tests (and the Scorecard) read from the single real
ingest built by `harness.EnrichmentHarness`."""

from dataclasses import dataclass, field

from app.core.enrichment_store import EnrichmentStore
from app.models.game_doc import GameDoc
from app.rag.retriever import GameRetriever
from tests.e2e.enrichment.game_case import GameCase


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
