"""GameCase — the declarative e2e test case: a corpus game + its recorded scraping + the
hand-written oracle. Plus loading the cases from the fixtures.

Choices:
  - the DTO is NOT duplicated in the fixture: it is read from the shared corpus
    (tests/fixtures/suites/core/games.json) by `id_product` → single source of truth.
  - the fixture (fixtures/<slug>.json) holds only what must be frozen / hand-written: the
    recorded scraping (`search_results` + `pages`) and the `oracle`. The runtime query is
    recomputed from the DTO with the REAL `WebEnricher._query`, so routing stays in lockstep with
    production code.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.enricher.web import WebEnricher
from app.models.game_doc import GameDoc

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


@dataclass(frozen=True)
class GameCase:
    """An e2e game: frozen DTO + recorded scraping + hand-written oracle."""

    slug: str
    id_product: int
    dto: dict                       # from the corpus
    query: str                      # WebEnricher._query(dto["name"]) — the routing key
    search_results: list[dict]      # recorded
    pages: dict[str, str]           # recorded {url: clean text}
    oracle: dict                    # hand-written (see fixtures/README.md)

    @property
    def name(self) -> str:
        return self.dto["name"]

    @property
    def must_find_queries(self) -> list[str]:
        return list(self.oracle.get("must_find_queries", []))

    @property
    def strip_certain(self) -> list[str]:
        """Certain DTO fields to BLANK before ingest, to 'encourage' the Web step (the Curator
        can't extract what isn't there → it lands in missing_info → the Web goes online). Empty =
        ingest the rich DTO as-is (used to verify the Web correctly does NOT fire)."""
        return list(self.oracle.get("strip_certain", []))

    @property
    def expect_web(self) -> bool:
        """Whether we expect the WebEnricher to fire for this game (asserted in phase 1)."""
        return bool(self.oracle.get("expect_web", False))

    def ingest_dto(self) -> dict:
        """The DTO actually fed to the pipeline: the corpus DTO with `strip_certain` fields
        blanked. The baseline uses this SAME dto → a fair 'same input, with vs without enrichment'
        comparison. The name is never blanked → the web query is unchanged, so the fixtures stay
        valid."""
        dto = dict(self.dto)
        for field in self.strip_certain:
            dto[field] = [] if isinstance(dto.get(field), list) else ""
        return dto

    def doc(self) -> GameDoc:
        """A fresh GameDoc from the (possibly stripped) DTO — what the ingester enriches."""
        return GameDoc.from_dto(self.ingest_dto())


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
