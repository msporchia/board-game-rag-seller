# Seller — advisor bot for choosing board games

> Codename: **Seller**. A Python (RAG) microservice alongside the GameNest PrestaShop that
> helps customers discover and choose board games in a conversational, guided, "salesperson"
> way — not a plain search engine.

---

## 1. Problem and goal

Customers know only a few games (Monopoly and little else) but the catalog is huge and
varied. We want a bot that:

- understands **vague, semantic** requests ("medieval games", "something like Chronicles of
  Avel") even when no matching categories/tags exist;
- filters on **concrete** criteria (player count, duration, age, complexity);
- proposes in an **appealing and fast** way: short text + **multiple-choice buttons**
  (people are lazy), so the conversation converges in a few clicks;
- **sells** the game (a convincing pitch, leveraging best-sellers and past purchases),
  not just links two titles;
- recommends **only games actually in the catalog and available** (never hallucinate titles).

Side goal (important): it is also a project to practice **LangChain + RAG** in depth. So we
proceed in stages, each one understandable.

---

## 2. Glossary (the 3 key concepts)

- **Embedding**: turning a text (a game description) into a vector of numbers that captures
  its *meaning*. Similar texts → nearby vectors. It lets us find "medieval" games or "like
  Avel" without any explicit tag.
- **Vector store**: a database specialized in quickly finding "the N nearest vectors" to a
  query (nearest neighbor). It also stores structured metadata (payload) to filter on →
  enables **hybrid search** (semantic + filters).
- **RAG (Retrieval-Augmented Generation)**: first we *retrieve* the relevant real games from
  our catalog (Retrieve), then we *inject* them into the LLM prompt (Augment), finally the
  LLM *writes* the pitch using only those games (Generate). Avoids hallucinations and keeps
  the bot anchored to the real catalog.

---

## 3. Technical decisions

| Topic | Choice | Notes |
|------|--------|------|
| Language | Python | microservice separate from the PHP |
| API framework | FastAPI | chat + ingest endpoints |
| RAG orchestration | LangChain | learning goal |
| Vector store | **Qdrant** (Docker) | powerful payload filters, same API local→prod |
| Embeddings | local: `nomic-embed-text` (Ollama) | prod: consider OpenAI `text-embedding-3` |
| LLM | local: `llama3.1` (Ollama) | prod: a more capable model (OpenAI/Claude) |
| Provider | **local-first**, swappable | LangChain abstraction to switch in prod |

**local→prod principle**: locally we run everything for free and offline (Ollama + Qdrant in
Docker). In production you only swap the providers (more capable embeddings/LLM) keeping the
architecture unchanged.

---

## 4. Data strategy (slow vs volatile vs contextual)

Not all data lives in the same place. A fundamental distinction:

| Type | Examples | Where it lives | Update |
|------|--------|-----------|---------------|
| **Slow** ("innate knowledge") | name, description, authors, mechanics, categories, player count, duration, age, complexity | **embedded in the vector store** (vector + payload) | only when the product content changes (MD5 diff) |
| **Volatile** | price, availability/stock | **NOT** embedded, fetched **live** via the PrestaShop API | at every recommendation |
| **Contextual** | user's latest N purchases, best-sellers by genre | fetched **live** via a privileged API | at every conversation |

**Incremental sync (MD5)**: instead of re-embedding the whole catalog, only the vector of the
products whose semantic content changed is recomputed. PrestaShop computes a hash of the
"slow" fields and notifies/exports only the deltas.

---

## 5. PrestaShop → Seller field mapping

Reference: the PHP module's constants (out of this repo).
The features live in `ps_feature` / `ps_feature_value` / `ps_feature_product`.

Verified on a real catalog snapshot (table prefix `ps_`, IT language = `id_lang` 1).
The features live in `ps_feature_product` → `ps_feature_value_lang` (values) / `ps_feature_lang` (names).
**Encoding**: the data is intact utf8mb4; the client/connector MUST use `utf8mb4`
(otherwise accents come out corrupted — it's just a connection issue, not a data one).

### TEXTUAL fields (→ embedding)
- `ps_product_lang.name`
- `ps_product_lang.description`
- `ps_product_lang.description_short`
- `FEAT_AUTORI` (5) — authors
- **`FEAT_TAG` (7) = mechanics + themes** ✅ confirmed. Multi-value per product, e.g.
  "Cooperativo", "Fantasy", "Gestione della Mano", "Lancio di dadi", "Piazzamento Tessere".
  A very strong signal for semantic search (and usable as a filter too).
- BGG (BoardGameGeek) enrichment present in the description

### STRUCTURED fields (→ payload / filters)
- `FEAT_NUM_PLAYER_EXPLODED` (28) — **EXPLODED player count**: one row per supported value
  (2,3,4,5…). It is THE field for the exact "game for 4" filter. ✅
- `FEAT_NUM_PLAYERS` (4) — displayed range "2-5" (for display, not for filtering)
- `FEAT_PLAY_TIME` (2) — duration in minutes (numeric)
- `FEAT_AGE` (1) — minimum age
- `FEAT_COMPLESSITA` (11) — weight/complexity, e.g. "Leggero (1)" (BGG scale)
- `FEAT_LANG` (3) — language
- `FEAT_ANNO_PUBBLICAZIONE` (13) — year
- `FEAT_INTERNAL_RATING` (6) — internal rating
- `FEAT_ESPANSIONE` (29) — Yes/No (to exclude/flag expansions)
- Categories: `CAT_GIOCHI_DA_TAVOLO` (10), `CAT_GIOCHI_DI_RUOLO` (24), `CAT_GIOCHI_DI_CARTE` (25)
- `FEAT_STATO` (12) — preorder/immediate/used (useful to filter availability)

### Catalog scale (snapshot)
- ~**32k** total active products
- ~**7.4k** active board games (category 10 + children) → corpus to embed
- No "Medieval" tag: confirms that requests like "medieval"/"like Avel" must be solved by
  **semantics**, not by an explicit tag.

---

## 6. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  PRESTASHOP (PHP)                                            │
│  • export/diff MD5 tool  ──(slow data, on-change)──┐        │
│  • privileged API: user-orders, price/stock ───────┼──┐     │
└─────────────────────────────────────────────────────┼──┼────┘
                                                       │  │
                          (incremental sync)           │  │ (live)
                                                       ▼  │
┌──────────────────────────────────────────────────────┼─────┐
│  PYTHON MICROSERVICE (FastAPI + LangChain)            │     │
│                                                       │     │
│  [Ingest] game description → embedding → Qdrant       │     │
│                                                       │     │
│  [Chat]  user ──► hybrid search (Qdrant) ──► RAG ─────┘     │
│                       │ filters: player count, duration     │
│                       └─ enriches with price/stock/orders   │
│                          ──► LLM (Ollama) ──► pitch+buttons │
└─────────────────────────────────────────────────────────────┘
                                                       │
                                              ┌────────▼────────┐
                                              │  chat FRONTEND  │
                                              │  text+buttons   │
                                              └─────────────────┘
```

### Containers (docker-compose)
- `seller-qdrant` — vector store (ports 6333 REST/dashboard, 6334 gRPC)
- `seller-ollama` — embeddings + LLM locally (port 11434)
- `seller-api` — FastAPI/LangChain microservice (port 8000)

Same `prestashop_network` network to reach PrestaShop/MySQL when needed.

---

## 7. API contracts (draft, to refine)

### Exposed by the Seller microservice
- `GET /health` — service status.
- `POST /ingest` — load/update games in the vector store (receives the MD5 deltas).
- `POST /chat` — input: user message + button choices + (opt.) user_id; output:
  text + list of recommended games + **quick replies** (buttons).

### Required from PrestaShop (privileged API, to implement on the PHP side)
- export of "slow data" + MD5 hash for the incremental diff;
- `GET` the logged-in user's latest N purchases;
- `GET` games for category X with feature Y;
- `GET` live price + availability for a list of `product_id`.

### Chat output (multiple-choice buttons)
The LLM replies in **structured JSON**: `{ "message": "...", "games": [...],
"quick_replies": ["Solo cooperativi", "Max 1 ora", "Sorprendimi"] }`.
The frontend draws the buttons; a click becomes a new filter in the hybrid search.

---

## 8. Phased roadmap

- [x] **Phase 0 — Infrastructure**: Qdrant + Ollama containers + FastAPI scaffold; working
  `docker compose up`. ✅ (catalog snapshot imported, /health OK)
- [x] **Phase 1 — Ingest + embedding**: games read from the enriched endpoint
  (`app/source.py`) → nomic embedding (768 dim) → Qdrant. ✅ validated (200 games, cosine;
  full catalog with `python -m app.ingest`).
- [x] **Phase 2 — Semantic retrieval**: `GameRetriever` + `/search` endpoint. ✅ works
  (the enriched text surfaces players/duration). ⚠️ Finding: `nomic-embed-text` is weak on
  Italian → test a better multilingual embedding (e.g. `bge-m3`).
- [x] **Phase 3 — Hybrid search**: filters (player count, duration, age, complexity) as Qdrant
  hard pre-filters + soft boost/rerank. ✅ (`app/rag/filters/`, `tests/unit/HybridSearch/`).
- [~] **Phase 4 — RAG**: LLM that writes the pitch over the retrieved games. ✅ first cut —
  stateless `POST /chat`, grounded structured output `{message, games, quick_replies}`, anti-
  hallucination validation + deterministic fallback (`app/chat/`, `tests/unit/ChatAdvisor/`).
  See [chat.md](chat.md) for findings + next levers (prose↔cards coherence, stronger model).
- [ ] **Phase 5 — Conversation + buttons**: stateful LangGraph over the Phase-4 core — chat
  memory, strategy routing, quick-reply clicks → filters, Haiku→Sonnet tiering.
- [~] **Phase 6 — Real sync + API**: ✅ enriched export endpoint ready (`controller=seller`);
  the live endpoints (price/stock, user orders) and the incremental re-ingest via
  `lastUpdateFrom` remain.

---

## Proposals / future ideas

To evaluate (detailed brain-dump in [note.md](note.md)):

- **Data quality check at ingest**: before indexing a game, verify the data quality (missing
  complexity, description too short, no tags…). If it fails → `low_quality` flag and special
  handling (e.g. proposed only as a last resort, with a stricter prompt).
- **LLM enrichment with online search** for games with poor or unusual data (just released,
  with no similar titles in the catalog): an LLM searches reviews/info online and fills the
  fields. ⚠️ **Zero hallucinations** — must be studied carefully (verified sources,
  validation, no inventions).
- **User memory**: latest N games visited (context) + profile (loves/hates/skill) + memory of
  past chats (summarized, marked "a while ago…").
- **Conversational strategy** (GUIDED / EXPLANATORY / DISCOVERY / QUICK MATCH) adapted to the
  user's level; confidence-based **model escalation** (Haiku→Sonnet).
- **Testing**: from a JSON input, generate test cases and test every phase.

---

## 9. Notes / open questions

- ✅ A real catalog snapshot is imported into the local MySQL for development.
- ✅ Mechanics resolved: they live in `FEAT_TAG` (7), see §5.
- Decide the **production** LLM/embeddings model (power vs cost).
- GPU for Ollama: optional locally (it works on CPU but slower).
