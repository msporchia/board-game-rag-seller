# Seller — microservice

RAG advisor bot for board games. Project docs in [`docs/`](docs/)
(`docs/seller.md` = overview, `docs/pipeline-dati.md` = data, `docs/note.md` = ideas).

A modular enrichment pipeline (citation-based Curator + optional web fallback) feeds hybrid
semantic search over Qdrant. FastAPI · LangChain · Ollama, local-first and provider-swappable.

## Quickstart (self-contained, offline)

The stack runs without a real PrestaShop/MySQL: a bundled **mock** serves the demo catalog
(50 games) over the same contract.

```bash
# 1. Start the stack (Qdrant + Ollama + API + mock catalog)
docker compose up -d
#    (NVIDIA GPU is optional: add -f docker-compose.gpu.yml)

# 2. Pull the models into Ollama (ONCE — the container starts empty)
docker exec seller-ollama ollama pull nomic-embed-text   # embeddings (needed for ingest/search)
docker exec seller-ollama ollama pull llama3.1            # LLM (only for enrichment/eval)

# 3. Ingest the demo catalog from the mock into Qdrant
docker compose exec seller-api python -m app.ingestion.ingester

# 4. Search
curl "http://localhost:8000/search?q=cooperativo+fantasy+per+due&k=5"
```

## Verify

- Seller API:    http://localhost:8000/health
- Mock catalog:  http://localhost:8001/health
- Qdrant:        http://localhost:6333/dashboard
- Ollama:        http://localhost:11434

## Tests & eval

```bash
docker compose exec seller-api python -m pytest tests/unit -q             # deterministic, offline
docker compose exec seller-api python -m tests.eval --suite core --k 5    # retrieval scorecard
```

## Data source

By default the API ingests from the bundled mock (`PRESTASHOP_BASE_URL=http://mock-prestashop:8001`).
Point it at a real PrestaShop "seller" endpoint to ingest a live catalog — see
[`.env.example`](.env.example) and [`docs/pipeline-dati.md`](docs/pipeline-dati.md).

## Structure

```
seller/
├── docker-compose.yml      # qdrant + ollama + api + mock catalog
├── docker-compose.gpu.yml  # optional NVIDIA override
├── Dockerfile
├── requirements.txt
├── mock/                   # mock PrestaShop "seller" endpoint (serves the DTO contract)
├── app/
│   ├── config.py           # configuration (env: Qdrant/Ollama/models/source)
│   ├── api/                # FastAPI routers (/health, /search)
│   ├── ingestion/          # source → enrichment pipeline → serializer
│   ├── core/               # vector store, enrichment store, web search
│   └── rag/                # retriever
└── tests/                  # unit (deterministic) + eval (LLM, record/replay)
```
