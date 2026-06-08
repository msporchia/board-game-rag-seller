"""Recorder — freezes the scraping of the e2e games (live web → JSON, once).

For each target game (picked from the corpus by id_product) it freezes the two non-deterministic
web inputs, using the REAL corpus name so the query matches production:
  1. the REAL search response to `WebEnricher._query(corpus_name)`;
  2. the REAL fetch of the pages (all ranked URLs, so the page cache fully covers the rails even
     if the ranking changes).

It does NOT write the oracle: the `oracle` block (queries, expect_web, strip_certain, ...) is
hand-written and PRESERVED across re-records — only the web data is refreshed.

Entry point: `python -m tests.e2e.enrichment record --ids 160,22,21` (see __main__.py).
"""

import json

from app.config import settings
from app.core.web_search import DdgsSearch, fetch_clean
from app.ingestion.enricher import WebEnricher
from tests.e2e.enrichment.cases import FIXTURES, load_corpus, query_for

# default = the two corpus games already battle-tested by the WebEnricher fixtures (Onitama,
# Viticulture) + a well-documented third one (Terraforming Mars).
DEFAULT_IDS = [160, 22, 21]
SLUGS = {160: "onitama", 22: "viticulture", 21: "terraforming-mars"}

_ORACLE_SKELETON = {
    "must_find_queries": [],
    "expect_keywords": [],
    "strip_certain": [],
    "expect_web": False,
    "note": "fill in by hand (see fixtures/README.md).",
}


def _slug(idp: int, name: str) -> str:
    if idp in SLUGS:
        return SLUGS[idp]
    base = name.split(" - ")[0].split(" | ")[0].strip().lower()
    return "".join(c if c.isalnum() else "-" for c in base).strip("-")


class Recorder:
    """Records the scraping fixtures for the target games, preserving the oracle."""

    def __init__(self):
        self._enr = WebEnricher()
        self._search = DdgsSearch()

    def record_one(self, dto: dict) -> dict:
        name = dto["name"]
        query = query_for(name)
        raw = self._search.search(query, settings.web_max_results)   # REAL search
        pages = {r.url: fetch_clean(r.url) for r in self._enr._ranked(raw)}  # REAL fetch, all ranked
        return {
            "id_product": int(dto["id_product"]),
            "name": name,            # informational (runtime recomputes the query from the corpus)
            "query": query,          # informational
            "recorded_with_model": settings.llm_model,
            "search_results": [r.model_dump() for r in raw],
            "pages": pages,
        }

    def record(self, ids: list[int]) -> None:
        corpus = load_corpus()
        FIXTURES.mkdir(parents=True, exist_ok=True)
        for idp in ids:
            if idp not in corpus:
                print(f"!! id {idp} not in corpus, skipping")
                continue
            dto = corpus[idp]
            out = FIXTURES / f"{_slug(idp, dto['name'])}.json"
            oracle = _ORACLE_SKELETON
            if out.exists():   # preserve the hand-written oracle
                oracle = json.loads(out.read_text(encoding="utf-8")).get("oracle", _ORACLE_SKELETON)

            fix = self.record_one(dto)
            fix["oracle"] = oracle
            out.write_text(json.dumps(fix, ensure_ascii=False, indent=2), encoding="utf-8")

            n_text = sum(1 for t in fix["pages"].values() if t)
            print(f"OK {out.name}: {len(fix['search_results'])} results, "
                  f"{len(fix['pages'])} pages ({n_text} with text) | query={fix['query']!r}")
