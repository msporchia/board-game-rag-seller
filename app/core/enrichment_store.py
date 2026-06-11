"""Enrichment store: DURABLE system-of-record of the enrichment work.

Separate from the vector store (Qdrant), which is just a REGENERABLE index. Here nothing is
thrown away (see docs): each game's curated record, the web-page cache and the provenance of
every extracted fact. This makes the re-ingest incremental (content_hash), avoids re-fetching
the same page and avoids re-calling the LLM for facts already extracted.

SQLite for now (single file, zero infra, local-first); the interface is meant to be
swappable with Postgres if/when scale demands it. Three tables:
  - products     GameDoc lifecycle (original/enriched/embed_text/missing_info/extracted)
  - web_pages    fetch cache (url → clean text)
  - extractions  facts extracted from the web with quote and provenance (→ source scoreboard)
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models.game_data import GameData
from app.models.game_doc import GameDoc

_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id_product    INTEGER PRIMARY KEY,
    content_hash  TEXT,
    name          TEXT,
    original_json TEXT NOT NULL,
    enriched_json TEXT NOT NULL,
    embed_text    TEXT,
    missing_info  TEXT NOT NULL DEFAULT '[]',
    extracted     TEXT NOT NULL DEFAULT '{}',
    low_quality   INTEGER NOT NULL DEFAULT 0,
    updated_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS web_pages (
    url         TEXT PRIMARY KEY,
    http_status INTEGER,
    clean_text  TEXT,
    fetched_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS extractions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    id_product    INTEGER NOT NULL,
    info          TEXT NOT NULL,
    value         TEXT NOT NULL,
    quote         TEXT,
    source_url    TEXT,
    source_domain TEXT,
    model         TEXT,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_extractions_product ON extractions(id_product);
CREATE INDEX IF NOT EXISTS idx_extractions_domain  ON extractions(source_domain);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EnrichmentStore:
    def __init__(self, path: str | None = None):
        self.path = path or settings.enrichment_db_path
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Additive migrations for DBs created before a column existed (SQLite has no
        ADD COLUMN IF NOT EXISTS). New columns must carry a DEFAULT so old rows stay valid."""
        cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(products)")}
        if "extracted" not in cols:
            self._conn.execute(
                "ALTER TABLE products ADD COLUMN extracted TEXT NOT NULL DEFAULT '{}'"
            )

    # ---- products: the game's curated record ----

    def save_game(self, doc: GameDoc, low_quality: bool = False) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO products
                   (id_product, content_hash, name, original_json, enriched_json,
                    embed_text, missing_info, extracted, low_quality, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id_product) DO UPDATE SET
                     content_hash=excluded.content_hash, name=excluded.name,
                     original_json=excluded.original_json, enriched_json=excluded.enriched_json,
                     embed_text=excluded.embed_text, missing_info=excluded.missing_info,
                     extracted=excluded.extracted,
                     low_quality=excluded.low_quality, updated_at=excluded.updated_at""",
                (doc.id_product, doc.content_hash, doc.original.name,
                 doc.original.model_dump_json(), doc.enriched.model_dump_json(),
                 doc.embed_text, json.dumps(doc.missing_info), json.dumps(doc.extracted),
                 int(low_quality), _now()),
            )
            self._conn.commit()

    def get_game(self, id_product: int) -> Optional[GameDoc]:
        row = self._conn.execute(
            "SELECT * FROM products WHERE id_product=?", (id_product,)
        ).fetchone()
        if not row:
            return None
        return GameDoc(
            original=GameData.model_validate_json(row["original_json"]),
            enriched=GameData.model_validate_json(row["enriched_json"]),
            embed_text=row["embed_text"],
            missing_info=json.loads(row["missing_info"]),
            extracted=json.loads(row["extracted"]),
        )

    def content_hash(self, id_product: int) -> Optional[str]:
        """For the incremental re-ingest: if unchanged, the game can be skipped."""
        row = self._conn.execute(
            "SELECT content_hash FROM products WHERE id_product=?", (id_product,)
        ).fetchone()
        return row["content_hash"] if row else None

    # ---- web_pages: fetch cache (no re-fetching) ----

    def save_page(self, url: str, http_status: int, clean_text: str) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO web_pages (url, http_status, clean_text, fetched_at)
                   VALUES (?,?,?,?)
                   ON CONFLICT(url) DO UPDATE SET
                     http_status=excluded.http_status, clean_text=excluded.clean_text,
                     fetched_at=excluded.fetched_at""",
                (url, http_status, clean_text, _now()),
            )
            self._conn.commit()

    def get_page(self, url: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT clean_text FROM web_pages WHERE url=?", (url,)
        ).fetchone()
        return row["clean_text"] if row else None

    # ---- extractions: provenance + source scoreboard ----

    def save_extraction(self, id_product: int, info: str, value: str, quote: str,
                        source_url: str, source_domain: str, model: str) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO extractions
                   (id_product, info, value, quote, source_url, source_domain, model, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (id_product, info, value, quote, source_url, source_domain, model, _now()),
            )
            self._conn.commit()

    def get_extractions(self, id_product: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM extractions WHERE id_product=? ORDER BY id", (id_product,)
        ).fetchall()
        return [dict(r) for r in rows]

    def source_scoreboard(self) -> list[dict]:
        """How many verified extractions each domain produced → reliability over time.
        This is the 'source scoreboard' feature, made free by the relational store."""
        rows = self._conn.execute(
            """SELECT source_domain, COUNT(*) AS n
               FROM extractions GROUP BY source_domain ORDER BY n DESC"""
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
