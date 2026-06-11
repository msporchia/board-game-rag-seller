SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT,
    component      TEXT,
    model          TEXT,
    prompt_chars   INTEGER,
    prompt_preview TEXT,
    response_chars INTEGER,
    input_tokens   INTEGER,
    output_tokens  INTEGER,
    duration_ms    REAL,
    error          TEXT,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_traces_component ON traces(component);
"""
