"""Records a game's fixture for the WebEnricher eval (live parts → JSON).

Does the non-deterministic parts once and freezes them:
  1. the REAL response to the search query (DDG);
  2. the REAL fetch of the pages the enricher would use (same order/stop as `assess`).

It does NOT generate the oracle: the `expect` block (ranking / judgment / extraction) is
written by hand by the human after looking at the recorded results. The 3 phases (see
`replay.py`) are each evaluated over their own piece of `expect`. The block scaffold is created
empty so that only CERTAIN assertions end up there — it's normal (and desired) for the oracle to
be partial.

Re-run when you add a game or when you want to re-record the sources.

    docker exec seller-api python -m tests.eval.WebEnricher.recorder \
        --slug viticulture --name "Viticulture" --missing ambientazione,durata,giocatori
"""

import argparse
import json

from app.config import settings
from app.core.web_search.ddgs import DdgsSearch
from app.core.web_search.fetcher import PageFetcher
from app.ingestion.enricher import WebEnricher
from tests.eval.WebEnricher.replay import FIXTURES


def _empty_expect(urls: list[str]) -> dict:
    """Oracle skeleton (partial): pre-populates the URL keys so the human sees right away what
    can be asserted. Leaves the values empty to avoid "default" oracles."""
    return {
        "ranking": {
            "top_domains": [],
            "must_drop_domains": [],
            "note": "fill in: the first N expected domains in `_ranked`; domains that must NOT appear"
        },
        "judgment": {url: {"note": "expected is_this_game / is_serious (omit if unsure)"}
                     for url in urls},
        "extraction": {url: {"note": "per info: {value_contains, quote_in_text: true}"}
                       for url in urls},
    }


def record(name: str, missing: list[str]) -> dict:
    enr = WebEnricher()

    # 1) REAL response to the query (raw search) → input to freeze
    raw = DdgsSearch().search(enr._query(name), settings.web_max_results)
    search_results = [r.model_dump() for r in raw]

    # 2) REAL fetch, replicating the order and stop-condition of WebEnricher.assess
    fetcher = PageFetcher()
    ranked = enr._ranked(raw)
    pages: dict[str, str] = {}
    fetched = 0
    for r in ranked:
        if fetched >= enr.max_sources:
            break
        text = fetcher.fetch(r.url)
        pages[r.url] = text
        if text:
            fetched += 1

    return {
        "name": name,
        "missing_info": missing,
        "recorded_with_model": settings.llm_model,
        "search_results": search_results,
        "pages": pages,
        "expect": _empty_expect(list(pages.keys())),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="fixture file name (e.g. viticulture)")
    ap.add_argument("--name", required=True, help="game name for the query")
    ap.add_argument("--missing", required=True, help="missing info, comma-separated")
    args = ap.parse_args()

    fix = record(args.name, [m.strip() for m in args.missing.split(",") if m.strip()])
    out = FIXTURES / f"{args.slug}.json"
    out.write_text(json.dumps(fix, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✓ recorded {out.name}: {len(fix['search_results'])} results, "
          f"{len(fix['pages'])} pages fetched")
    print("  Pages (quickly check the text and fill in `expect` by hand):")
    for url, text in fix["pages"].items():
        first = (text[:120] + "…") if len(text) > 120 else text
        print(f"   - {url}\n       {first!r}")


if __name__ == "__main__":
    main()
