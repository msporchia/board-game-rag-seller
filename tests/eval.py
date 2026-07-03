"""Retrieval evaluation harness, organized into SUITES.

A suite (tests/fixtures/suites/<name>/) has:
  - games.json   frozen corpus (~50 real DTOs)
  - labels.json  structured oracle: { "id": ["tag", ...] }  (bootstrapped from catalog tags)
  - queries.json [ { "query": "...", "tags": ["Cooperativo"] } ]

Relevant(query) = games whose labels contain ALL the query's tags.
Per-query metrics:
  - Recall@K, Precision@K
  - err = normalized inversions (fraction of relevant/irrelevant pairs mis-ordered,
    0 = perfect, ≈ 1−AUC): "an irrelevant above a relevant" is an error.

`--pipeline` chooses the enricher chain applied to the data before embedding.

    docker exec seller-api python -m tests.eval --suite core --k 5 --pipeline trim
"""

import argparse
import json
from pathlib import Path

from app.core.vector_store import GameVectorStore
from app.ingestion.enricher.compose import RuleComposeEnricher
from app.ingestion.enricher.curator import CuratorEnricher
from app.ingestion.enricher.pipeline import EnrichmentPipeline
from app.ingestion.enricher.synth import SynthEnricher
from app.ingestion.enricher.trim import TrimEnricher
from app.ingestion.ingester import Ingester
from app.ingestion.sources.json_source import JsonSource
from app.rag.retriever import GameRetriever
from tests.eval_variants.append_synth_enricher import AppendSynthEnricher
from tests.eval_variants.uncapped_compose_enricher import UncappedComposeEnricher

SUITES = Path(__file__).parent / "fixtures" / "suites"

# Pipeline configurations comparable on the harness (each ends with a compose).
# The text-budget experiment variants (SEL-144, docs/experiments.md rows 7-8) live in
# tests/eval_variants/ — one class per file, measurement-only, never production.
PIPELINES = {
    "rule": [RuleComposeEnricher()],                    # baseline: deterministic compose
    "trim": [TrimEnricher(350), RuleComposeEnricher()],  # aggressive-cut experiment (§6); the default is the 1000 failsafe
    "curator": [CuratorEnricher(), RuleComposeEnricher()],  # SEMANTIC compression (LLM) + compose
    "synth": [CuratorEnricher(), SynthEnricher(), RuleComposeEnricher()],  # the missing link: fuse facts into the text
    # saturation/dilution cell: full original description, zero LLM
    "rule-uncapped": [UncappedComposeEnricher()],
    # additive synth counter-proof: full description + fused synth layer on top (uncapped
    # compose, otherwise the appended layer would just be truncated away)
    "synth-append": [CuratorEnricher(), AppendSynthEnricher(), UncappedComposeEnricher()],
}


def relevant_ids(query_tags: list[str], labels: dict) -> set[int]:
    qt = set(query_tags)
    return {int(gid) for gid, tags in labels.items() if qt.issubset(set(tags))}


def run(suite: str = "core", k: int = 5, pipeline: str = "rule") -> None:
    base = SUITES / suite
    games = json.loads((base / "games.json").read_text(encoding="utf-8"))
    labels = json.loads((base / "labels.json").read_text(encoding="utf-8"))
    queries = json.loads((base / "queries.json").read_text(encoding="utf-8"))

    collection = f"games_test_{suite}_{pipeline}"
    store = GameVectorStore(collection_name=collection)
    print(f"Suite '{suite}' | pipeline='{pipeline}' | {len(games)} games, {len(queries)} queries")
    Ingester(
        source=JsonSource(games),
        store=store,
        pipeline=EnrichmentPipeline(PIPELINES[pipeline]),
    ).run(recreate=True)
    retriever = GameRetriever(store=store)
    n_games = len(games)

    sum_recall = sum_prec = sum_err = 0.0
    clean = 0
    print(f"\n===========  SCORECARD '{suite}' pipeline='{pipeline}' (K={k})  ===========")
    for item in queries:
        q, tags = item["query"], item["tags"]
        rel = relevant_ids(tags, labels)
        ranked = [h.id_product for h in retriever.search(q, k=n_games)]  # full ranking
        topk = ranked[:k]
        hit = len(rel & set(topk))
        recall = hit / len(rel) if rel else 0.0
        prec = hit / k

        # inversions: for each relevant, how many irrelevant above it; normalized
        inv = seen_irrel = 0
        for gid in ranked:
            if gid in rel:
                inv += seen_irrel
            else:
                seen_irrel += 1
        n_irrel = n_games - len(rel)
        err = inv / (len(rel) * n_irrel) if rel and n_irrel else 0.0
        first_rel = next((i + 1 for i, gid in enumerate(ranked) if gid in rel), None)

        sum_recall += recall
        sum_prec += prec
        sum_err += err
        if err == 0:
            clean += 1
        flag = "✓" if err == 0 else "✗"
        print(f" {flag} R@{k}={recall:.2f} P@{k}={prec:.2f} err={err:.2f} 1st-rel=#{first_rel} "
              f"| rel={len(rel):>2} | {q}")

    n = len(queries)
    print(f"\n---  AVERAGES: Recall@{k}={sum_recall / n:.2f} | Precision@{k}={sum_prec / n:.2f} "
          f"| avg err={sum_err / n:.2f} | clean queries={clean}/{n}  ---")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="core")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--pipeline", choices=list(PIPELINES), default="rule")
    run(**vars(ap.parse_args()))
