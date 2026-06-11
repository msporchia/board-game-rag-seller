"""Loading the e2e cases from the fixtures (the `GameCase` shape lives in `game_case.py`).

Choices:
  - the DTO is NOT duplicated in the fixture: it is read from the shared corpus
    (tests/fixtures/suites/core/games.json) by `id_product` → single source of truth.
  - the fixture (fixtures/<slug>.json) holds only what must be frozen / hand-written: the
    recorded scraping (`search_results` + `pages`) and the `oracle`. The runtime query is
    recomputed from the DTO with the REAL `WebEnricher._query`, so routing stays in lockstep with
    production code.
"""

import json
from pathlib import Path

from app.ingestion.enricher.web import WebEnricher
from tests.e2e.enrichment.game_case import GameCase

CORPUS = Path(__file__).resolve().parents[2] / "fixtures" / "suites" / "core" / "games.json"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# a single instance, only to reuse the REAL query builder (no network in the constructor).
_QUERY = WebEnricher()


def query_for(name: str) -> str:
    """The exact search query the WebEnricher would issue for this game."""
    return _QUERY._query(name)


def load_corpus() -> dict[int, dict]:
    games = json.loads(CORPUS.read_text(encoding="utf-8"))
    return {int(g["id_product"]): g for g in games}


def load_cases() -> list[GameCase]:
    """Every fixtures/<slug>.json joined with its corpus DTO."""
    corpus = load_corpus()
    cases: list[GameCase] = []
    for path in sorted(FIXTURES.glob("*.json")):
        fix = json.loads(path.read_text(encoding="utf-8"))
        idp = int(fix["id_product"])
        if idp not in corpus:
            raise KeyError(f"{path.name}: id_product {idp} not in corpus {CORPUS.name}")
        dto = corpus[idp]
        cases.append(GameCase(
            slug=path.stem,
            id_product=idp,
            dto=dto,
            query=query_for(dto["name"]),
            search_results=fix.get("search_results", []),
            pages=fix.get("pages", {}),
            oracle=fix.get("oracle", {}),
        ))
    return cases
