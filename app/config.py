"""Seller microservice configuration.

Reads environment variables (defined in docker-compose). Locally they point at the
containers; in production you only change these values to use different providers/endpoints
without touching the rest of the code.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    qdrant_url: str = "http://seller-qdrant:6333"
    ollama_url: str = "http://seller-ollama:11434"
    embedding_model: str = "nomic-embed-text"
    llm_model: str = "llama3.1"
    # Chat model tiering (Phase 5): the model the generate step escalates to when the analyze
    # step sets `escalate=true`. Empty → falls back to `llm_model`, so locally the escalation
    # CONTRACT is exercised end-to-end as a no-op; in production point it at a stronger model
    # (e.g. a larger local model, or Sonnet behind a provider-swappable transport).
    llm_model_strong: str = ""

    # Qdrant collection that holds the games
    collection_name: str = "games"

    # --- Data source: PrestaShop "seller" endpoint (see docs/pipeline-dati.md) ---
    prestashop_base_url: str = "http://catalog-ps"  # reachable on the docker network
    # The shop's canonical domain is "localhost": we connect to the container but send
    # this Host header, otherwise PrestaShop issues a 301 redirect to localhost.
    prestashop_host_header: str = "localhost"
    seller_token: str = "CHANGEME_TOKEN"          # override via env; depends on the installation
    seller_page_size: int = 100

    # --- Enrichment store (durable system-of-record, separate from the vector store) ---
    # /app is the bind mount of ./seller → the DB persists on the host and is inspectable.
    enrichment_db_path: str = "/app/data/seller.db"

    # --- Chat memory (Phase 5): LangGraph checkpointer storage, same data/ layout ---
    chat_checkpoint_db_path: str = "/app/data/chat_sessions.db"

    # --- Observability (docs/observability.md) ---
    log_level: str = "INFO"        # LOG_LEVEL: root logging level for API and ingester CLI
    trace_backend: str = "sqlite"  # TRACE_BACKEND: sqlite (local `traces` table) | off

    # --- WebEnricher: online search (fallback, see docs) ---
    web_search_region: str = "it-it"
    # Browser UA: many sources block "bare" fetchers (403/401).
    web_user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    web_max_results: int = 8          # results requested from the search engine
    web_max_sources: int = 3          # pages actually fetched and extracted
    web_fetch_chars: int = 6000       # text cap per source handed to the LLM
    # Trust whitelist (UPDATABLE data, not hardcoded in the logic): known-good domains get
    # priority; unknown ones go through the LLM judgment. Empirically rich for board-game
    # reviews.
    web_trusted_domains: list[str] = [
        "goblins.net",            # La Tana dei Goblin (entry + IT reviews)
        "balenaludens.it",
        "houseofgames.it",
        "giochisulnostrotavolo.it",
        "gioconomicon.net",
        "lamascherariposta.it",
        "shutupandsitdown.com",
        "therewillbe.games",
    ]
    # Blocklist (updatable data): always discarded. Our own shop (extracting from it would
    # be circular) + known retailers (product listings, not reviews → weak source).
    web_blocked_domains: list[str] = [
        "gamenest.example",       # ourselves
        "dungeondice.it", "frogames.it", "ibs.it", "libreriasemola.it",
        "amazon.it", "amazon.com", "ebay.it",
    ]


settings = Settings()
