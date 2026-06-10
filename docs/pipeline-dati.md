# Data pipeline and ingestion contract

## Principle: Seller consumes a contract, not the DB

Seller does not read the PrestaShop database: it consumes an **API that returns the
already-enriched products** (DTO) under a **stable contract**.

- **Decoupling (Anti-Corruption Layer)**: if the way data is managed inside PrestaShop
  changes (features, categories, etc.), **only** the PHP endpoint is updated — the contract
  toward Seller stays identical.
- **Multi-source**: every source (PrestaShop today, other catalogs/BGG tomorrow) maps to
  the canonical `GameDoc` model.
- **Delta / upsert**: the API exposes the changes (hash or timestamp), so only what changed
  is re-embedded.

```
PrestaShop (PHP)                         Seller (Python)
┌────────────────────────┐              ┌─────────────────────────┐
│ features, categories,  │   HTTP API   │ Source → GameDoc         │
│ descriptions, BGG ──────┼─ contract ──▶│ (canonical model)        │
│  = raw/sparse data     │   stable     │   → embedding → Qdrant   │
│  → enriched into a DTO │   (DTO)      │   → upsert by id         │
└────────────────────────┘              └─────────────────────────┘
        the ACL lives here                indifferent to the source
```

## Slow vs volatile data

- **Slow** (embedded in the vector store): name, description, tags/mechanics, authors,
  player count, duration, age, complexity, year, rating. They change rarely.
- **Volatile** (NOT embedded, fetched **live** at recommendation time): price,
  availability/stock.

## Derived / derivable fields (future — for hybrid filters)

Beyond the slow fields above, there is a class of **status/flag** attributes that would make good
extra hybrid-search filters (Phase 3) and good pitch signals: e.g. **preorder**, **new release**,
**best-seller**, **on sale**, used/damaged, language availability. PrestaShop already models some
(`FEAT_STATO` = preorder/immediate/used; year). The rule of thumb:

- **Prefer the source.** When the field is a real attribute, it should come **through the DTO
  contract** (the PHP ACL adds it once, every consumer benefits) — not be guessed downstream.
- **Derive only as a fallback.** When the source can't give it, we can derive it ourselves from
  data we already have — e.g. "new release" from `year` (or a release date) relative to *now*,
  "best-seller" from sales/rating signals. Derived fields are second-class: lower confidence,
  and they belong next to the enrichment (provenance), not silently in the payload.

Not built yet. Flagged here because these are cheap, likely-useful filters/labels to add once we
decide which come from the source and which we derive — worth measuring whether they actually
improve retrieval/conversion before wiring them in.

## The contract (enriched product DTO)

The API returns objects with this shape (mirrors `app/models.py:GameDoc`):

```json
{
  "id_product": 1,
  "content_hash": "e0eee5af...",          // changes only if the "slow" content changes (for the deltas)
  "name": "Massive Darkness ...",
  "description": "Text already cleaned of HTML ...",
  "tags": ["Cooperativo", "Fantasy", "Dungeon Crawler", "Lancio di dadi"],
  "autori": "Raphaël Guiton, ...",
  "players": [1, 2, 3, 4, 5, 6],           // EXPLODED player count → exact filter
  "players_display": "1-6",
  "duration_min": 120,
  "age_min": 14,
  "complexity": "Medio (3)",
  "complexity_level": 3,                    // numeric level extracted
  "year": 2017,
  "internal_rating": 7.2,
  "is_expansion": false,
  "categoria": "Giochi da tavolo > Giochi di Avventura",
  "marca": "Asmodee",
  "image": "https://img.gamenest.example/1-large_default/...jpg"
}
```

Price and stock are **not** in the ingest contract (volatile → live).

## PrestaShop-side endpoint (`utils` module)

✅ **Implemented** — enriched export of the board games:

```
index.php?fc=module&module=utils&controller=seller&token=<TOKEN>
         &page=1&pageSize=100[&lastUpdateFrom=YYYY-MM-DD HH:MM:SS][&ids=1,2,3]
```

- Response: `{ products: [DTO], page, pageSize, hasNext }` (paginated).
- `lastUpdateFrom` → only the **deltas** (incremental re-ingest). `ids` → pinpoint filter.
- Token: derived from the installation key (local value redacted). With `&debug=1` and a
  wrong token the endpoint prints the correct one.
- Code: the producer lives in the PHP module (out of this repo). Scope: board games
  (cat. 10 + children), used/damaged excluded.

**Future** endpoints (live): price+stock for a list of ids; user's latest purchases;
best-sellers by genre.

## Seller-side ingestion flow

```
Source → EnrichmentPipeline → Composer → serializer → VectorStore
                                            └→ EnrichmentStore (durable curated record)
```

1. **Source** (`app/ingestion/sources.py`): reads the DTOs (PrestaShop or JSON) → `GameDoc`.
   Prepares the data, does not decide the text.
2. **EnrichmentPipeline** (`app/ingestion/enricher/`): ordered chain of `Enricher`
   (**Strategy** + **Chain of Responsibility** patterns), each with a *guard* (acts only when
   needed). Works on the **DATA** (`GameDoc`). Today:
   - `TrimEnricher` (deterministic FAILSAFE, default ~1000 chars): pre-LLM cap against
     abnormal descriptions (cost/token control). Only fires on outliers.
   - `CuratorEnricher` (LLM, **citation-based**): classifies the 7 REQUIRED INFO as
     present/missing and extracts normalized values FROM THE TEXT; it does NOT touch the
     description (no synthesis). For each label it requires `{where, quote, normalized_value}`
     and VALIDATES the verbatim quote (anti-hallucination). Output: updates
     `game.missing_info` ← missing, `game.extracted` ← extracted, `enriched.tags` ←
     deduced mechanics (if empty).
   - `WebEnricher` (online FALLBACK, runs ONLY if gaps remain in `missing_info`): mini-RAG
     with citation-based verification (same pattern as the Curator, applied to real pages).
   - `SynthEnricher` (TODO): produces the unified SYNTHESIS over rich material
     (`certain_data + game.extracted + web facts + multi-source source_descriptions`) and
     writes it into `enriched.description`. Moved out of the Curator after measuring that
     compressing in there lost recall (v1 0.23 < 0.26 baseline).
   - Stubs: `extract`/`augment`/`gapfill`.
3. **Composer** (`RuleComposeEnricher`): a SINGLE step that composes the **text** to embed —
   word order/coherence matters. Deterministic baseline (the synthesis is written upstream by
   the `SynthEnricher`).
4. **VectorStore** (`app/core/vector_store.py`): embedding + upsert to Qdrant. Stable point
   id (uuid5 of `id_product`) → re-ingest = upsert, no duplicates.
5. **EnrichmentStore** (`app/core/enrichment_store.py`, SQLite): in parallel, persists the
   curated record (durable system-of-record), separate from the regenerable Qdrant index.

## File map

| File | Role |
|------|------|
| PHP `Seller` module (out of repo) | Contract producer (PHP): assembles the enriched DTO. |
| `app/models.py` | `GameDoc` (`original` + `enriched` + `embed_text` + `missing_info` + **`extracted`** dict) + `GameHit`. |
| `app/ingestion/sources.py` | Source: DTO → `GameDoc` (`PrestashopSource`, `JsonSource`). |
| `app/ingestion/enricher/` | Package: one file per enricher (`base`, `trim`, `compose`, `curator`, `web`, stubs `extract`/`augment`/`gapfill`). |
| `app/ingestion/serializer.py` | `DocumentSerializer`: `GameDoc` → Document (page_content=embed_text + payload). |
| `app/ingestion/ingester.py` | Orchestration: source → pipeline → serializer → Qdrant (+ EnrichmentStore). |
| `app/core/web_search/` | Package: `DdgsSearch` (search, swappable ABC) + `PageFetcher` (httpx UA + trafilatura), both injected into the WebEnricher. |
| `app/core/enrichment_store.py` | `EnrichmentStore` (SQLite): curated record + page cache + provenance. |
| `app/core/vector_store.py` | `GameVectorStore` (embeddings + Qdrant). |
| `app/rag/retriever.py` | `GameRetriever` (semantic search). |
| `app/api/*` | FastAPI endpoints (`/health`, `/search`). |
