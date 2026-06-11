"""GameCase — the declarative e2e test case: a corpus game + its recorded scraping + the
hand-written oracle. Loading from the fixtures lives in `cases.py`.
"""

from dataclasses import dataclass

from app.models.game_doc import GameDoc


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
