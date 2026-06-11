"""Manual end-to-end run of the WebEnricher on a real game.

Shows: clean query, search results with the whitelist flag, VERIFIED facts per source, and the
final text block with provenance. Meant to "see the process", it is not a test.

    docker exec seller-api python -m tests.try_web \
        --name "Viticulture Essential Edition - Gioco Strategico" \
        --missing "ambientazione/tema,meccaniche principali,a chi è adatto"
"""

import argparse

from app.ingestion.enricher.web import WebEnricher
from app.models.game_doc import GameDoc


def run(name: str, missing: list[str]) -> None:
    we = WebEnricher()
    doc = GameDoc.from_dto({"id_product": 0, "name": name}).model_copy(
        update={"missing_info": missing}
    )

    query = we._query(name)
    print(f"\nCATALOG name : {name}")
    print(f"CLEAN name   : {we._clean_name(name)}")
    print(f"QUERY        : {query}")
    print(f"MISSING      : {missing}\n")

    results = we._ranked(we.search_provider.search(query, 8))
    print("RESULTS (ordered: whitelist first):")
    for r in results:
        flag = "★ trusted" if r.domain in we.trusted else "  unknown"
        print(f"  [{flag}] {r.domain:28} {r.url}")

    print("\n--- assess (fetch + judgment + verified extraction) ---")
    a = we.assess(doc)
    if not a["facts"]:
        print("  (nothing verified online)")
    for info, entries in a["facts"].items():
        for e in entries:
            print(f"  • {info}: {e['value']}  [source: {e['source']}]")
    print(f"\nSOURCES used: {a['sources']}")

    out = we.enrich(doc)
    print("\n--- enriched description (enters the embed_text) ---")
    print(out.enriched.description)
    print(f"\nResidual MISSING (for a possible next step): {out.missing_info}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--missing", default="ambientazione/tema,meccaniche principali,a chi è adatto")
    args = ap.parse_args()
    run(args.name, [m.strip() for m in args.missing.split(",") if m.strip()])
