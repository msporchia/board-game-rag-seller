"""`setup_logging`: configured once, idempotent, level from settings (env LOG_LEVEL)."""

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
