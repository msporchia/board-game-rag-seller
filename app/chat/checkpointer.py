import sqlite3
from pathlib import Path

from app.config import settings


def sqlite_checkpointer():
    """Default session storage: SqliteSaver on a local file under data/ (next to seller.db).

    `check_same_thread=False` because FastAPI serves sync handlers from a threadpool; SqliteSaver
    serializes access internally. Tests pass an InMemorySaver instead; production would pass a
    PostgresSaver/RedisSaver — the graph does not care (see the graph module docstring).
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    path = Path(settings.chat_checkpoint_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver(sqlite3.connect(str(path), check_same_thread=False))
