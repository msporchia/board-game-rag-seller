"""UncappedComposeEnricher: the saturation/dilution cell of the text-budget experiments.

Measurement variant, NOT production: the deterministic compose without the 1800-char
description cap (a nomic-era dilution tuning), so the embedder sees the full original text.
It falsified the "give the strong embedder everything" hypothesis — semantic dilution survives
bge-m3 (ledger row 7 in docs/experiments.md). Runnable as `--pipeline rule-uncapped`.
"""

from app.ingestion.enricher.compose import RuleComposeEnricher


class UncappedComposeEnricher(RuleComposeEnricher):
    MAX_DESCRIPTION_CHARS = 100_000
