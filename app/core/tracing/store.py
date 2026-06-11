import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import settings
from app.core.tracing.schema import SCHEMA


class TraceStore:
    """Durable record of LLM calls. Sibling of `EnrichmentStore` (same SQLite/WAL pattern,
    same DB file by default) but a separate class: observability must not leak into the
    system-of-record's concerns, and either can be swapped independently."""

    def __init__(self, path: str | None = None):
        self.path = path or settings.enrichment_db_path
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def save_trace(self, run_id: str, component: str, model: Optional[str],
                   prompt_chars: int, prompt_preview: str,
                   response_chars: Optional[int] = None,
                   input_tokens: Optional[int] = None, output_tokens: Optional[int] = None,
                   duration_ms: Optional[float] = None, error: Optional[str] = None) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO traces
                   (run_id, component, model, prompt_chars, prompt_preview, response_chars,
                    input_tokens, output_tokens, duration_ms, error, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, component, model, prompt_chars, prompt_preview, response_chars,
                 input_tokens, output_tokens, duration_ms, error,
                 datetime.now(timezone.utc).isoformat()),
            )
            self._conn.commit()

    def get_traces(self, component: str | None = None) -> list[dict]:
        if component:
            rows = self._conn.execute(
                "SELECT * FROM traces WHERE component=? ORDER BY id", (component,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM traces ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
