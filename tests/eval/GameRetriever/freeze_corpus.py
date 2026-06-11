"""Freezes the POST-PIPELINE corpus for the GameRetriever ranking eval (LLM → JSON, once).

The ranking eval must search over the data shape the retriever sees in PRODUCTION — the output
of the enrichment chain — not over raw catalog marketing. This script runs the production
chain minus the Web step (Curator → Synth → Compose; Web is a network gap-fill fallback, so
excluding it keeps the freeze reproducible offline) over the shared fixture corpus ONCE, and
freezes the resulting GameDocs to `games_enriched.json` next to `games.json`.

The freeze is INCREMENTAL: each game is appended to the output as soon as it is enriched, and
already-frozen ids are skipped on re-run — a crashed/interrupted run resumes where it left off.
Delete the output file to re-freeze from scratch (e.g. after a curator/synth prompt change).

    docker compose exec seller-api python -m tests.eval.GameRetriever.freeze_corpus
"""

import json
import time
from pathlib import Path

from app.core.logging import get_logger, setup_logging
from app.ingestion.enricher.compose import RuleComposeEnricher
from app.ingestion.enricher.curator import CuratorEnricher
from app.ingestion.enricher.pipeline import EnrichmentPipeline
from app.ingestion.enricher.synth import SynthEnricher
from app.models.game_doc import GameDoc

logger = get_logger(__name__)

SUITE = Path(__file__).resolve().parents[2] / "fixtures" / "suites" / "core"
CORPUS = SUITE / "games.json"
FROZEN = SUITE / "games_enriched.json"


class CorpusFreezer:
    """Runs the offline production chain over the fixture corpus and freezes the GameDocs."""

    def __init__(self, pipeline: EnrichmentPipeline | None = None):
        self.pipeline = pipeline or EnrichmentPipeline([
            CuratorEnricher(), SynthEnricher(), RuleComposeEnricher(),
        ])

    def run(self) -> int:
        dtos = json.loads(CORPUS.read_text(encoding="utf-8"))
        frozen: list[dict] = (json.loads(FROZEN.read_text(encoding="utf-8"))
                              if FROZEN.exists() else [])
        done = {doc["original"]["id_product"] for doc in frozen}

        todo = [dto for dto in dtos if dto["id_product"] not in done]
        logger.info("freeze_start", corpus=len(dtos), frozen=len(done), todo=len(todo))
        for i, dto in enumerate(todo, 1):
            t0 = time.perf_counter()
            doc = self.pipeline.run(GameDoc.from_dto(dto))
            frozen.append(doc.model_dump(mode="json"))
            FROZEN.write_text(json.dumps(frozen, ensure_ascii=False, indent=2),
                              encoding="utf-8")
            logger.info("game_frozen", game=doc.id_product, name=doc.original.name,
                        progress=f"{i}/{len(todo)}",
                        duration_ms=round((time.perf_counter() - t0) * 1000))
        logger.info("freeze_done", total=len(frozen), path=str(FROZEN))
        return len(frozen)


if __name__ == "__main__":
    setup_logging()
    CorpusFreezer().run()
