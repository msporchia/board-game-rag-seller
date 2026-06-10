"""`get_trace_callbacks` factory: the only place that knows the tracing backend.

The factory is driven by `settings.trace_backend` (env `TRACE_BACKEND`); the tests
monkeypatch the setting — no env juggling, no I/O (the handler opens its store lazily).
"""

from app.config import settings
from app.core.tracing import SQLiteTraceHandler, get_trace_callbacks


def test_sqlite_backend_returns_tagged_handler(monkeypatch):
    monkeypatch.setattr(settings, "trace_backend", "sqlite")
    callbacks = get_trace_callbacks("curator")
    assert len(callbacks) == 1
    assert isinstance(callbacks[0], SQLiteTraceHandler)
    assert callbacks[0].component == "curator"


def test_off_backend_returns_no_callbacks(monkeypatch):
    monkeypatch.setattr(settings, "trace_backend", "off")
    assert get_trace_callbacks("curator") == []


def test_backend_name_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(settings, "trace_backend", "OFF")
    assert get_trace_callbacks("web") == []


def test_unknown_backend_disables_tracing_with_warning(monkeypatch, caplog):
    monkeypatch.setattr(settings, "trace_backend", "wat")
    with caplog.at_level("WARNING", logger="app.core.tracing"):
        assert get_trace_callbacks("synth") == []
    assert any("TRACE_BACKEND" in r.message for r in caplog.records)
