# E2E enrichment fixtures — schema

One `<slug>.json` per game. The **recorded** part (scraping) is regenerated with the `record`
command; the **oracle** part is hand-written and preserved across re-records.

```jsonc
{
  "id_product": 22,                  // key into the corpus (games.json) — the DTO is NOT duplicated here
  "name": "...",                     // informational (the runtime query is recomputed from the corpus)
  "query": "...",                    // informational: WebEnricher._query(name)
  "recorded_with_model": "llama3.1",
  "search_results": [ {"title","url","snippet"}, ... ],  // RECORDED (frozen input)
  "pages": { "url": "clean text", ... },                 // RECORDED (page-cache seed)

  "oracle": {                        // HAND-WRITTEN
    "must_find_queries": ["..."],    // common user-like queries that must retrieve the game (phase 3)
    "expect_keywords":   ["..."],    // expected thematic terms in the text (no rulebook details)
    "strip_certain":     ["description"], // DTO fields to blank pre-ingest to "encourage" the Web
    "expect_web":        true,       // do we expect the WebEnricher to fire? (phase 1)
    "note": "..."
  }
}
```

Note: `must_find_queries` and the corpus text stay in Italian on purpose — they are user-facing
input over an Italian catalog. See `../README.md` for the philosophy (first screen) and
`docs/enrichment/e2e-findings.md` for the results.
