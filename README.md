# Seller — microservice

RAG advisor bot for board games. Project docs in [`docs/`](docs/)
(`docs/seller.md` = overview, `docs/pipeline-dati.md` = data, `docs/note.md` = ideas).

## Start (Phase 0)

```bash
# From the repo root: start the Seller project containers
docker compose up -d seller-qdrant seller-ollama seller-api

# Pull the models into Ollama (ONCE — the container starts empty)
docker exec seller-ollama ollama pull nomic-embed-text   # embeddings
docker exec seller-ollama ollama pull llama3.1            # LLM
```

## Verify

- Seller API:    http://localhost:8000/health
- Qdrant:        http://localhost:6333/dashboard
- Ollama:        http://localhost:11434

## Structure

```
seller/
├── Dockerfile
├── requirements.txt
└── app/
    ├── config.py    # configuration (env: Qdrant/Ollama/models)
    └── main.py      # FastAPI (Phase 0: /health)
```
