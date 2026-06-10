"""`setup_logging`: configured once, idempotent, level from settings (env LOG_LEVEL),
renderer from LOG_FORMAT (console for humans, json for platforms)."""

import io
import json
import logging

import pytest

import app.core.logging as app_logging
from app.config import settings


@pytest.fixture
def fresh_root(monkeypatch):
    """Reset the module's configured flag and restore the root logger afterwards."""
    monkeypatch.setattr(app_logging, "_configured", False)
    root = logging.getLogger()
    old_level, old_handlers = root.level, list(root.handlers)
    root.handlers[:] = []  # force setup_logging to attach its own handler
    yield root
    root.setLevel(old_level)
    root.handlers[:] = old_handlers


def test_setup_is_idempotent(fresh_root):
    app_logging.setup_logging()
    n_handlers = len(fresh_root.handlers)
    app_logging.setup_logging()  # second call: no stacking, no reconfiguration
    app_logging.setup_logging()
    assert len(fresh_root.handlers) == n_handlers


def test_level_comes_from_settings(fresh_root, monkeypatch):
    monkeypatch.setattr(settings, "log_level", "debug")
    app_logging.setup_logging()
    assert fresh_root.level == logging.DEBUG


def test_explicit_level_overrides_settings(fresh_root, monkeypatch):
    monkeypatch.setattr(settings, "log_level", "INFO")
    app_logging.setup_logging(level="WARNING")
    assert fresh_root.level == logging.WARNING


def test_events_carry_fields_not_prose(monkeypatch):
    """The structured contract: an event logged with fields comes out as fields —
    machine-parseable with LOG_FORMAT=json, one JSON object per line. Tested at the
    formatter level: under pytest the root logger already has caplog's handler, so
    `setup_logging` (correctly) refuses to attach its own."""
    monkeypatch.setattr(settings, "log_format", "json")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(app_logging._formatter())
    target = logging.getLogger("contract_test")
    target.addHandler(handler)
    target.setLevel(logging.INFO)
    target.propagate = False
    try:
        app_logging.get_logger("contract_test").warning("an_event", game=2845, hits=0)
    finally:
        target.removeHandler(handler)
        target.propagate = True
    data = json.loads(stream.getvalue().strip())
    assert data["event"] == "an_event"
    assert data["game"] == 2845
    assert data["hits"] == 0
    assert data["level"] == "warning"
    assert data["logger"] == "contract_test"
