"""ExchangeTransport.call() blocks until the reply file exists, polling rather than racing —
the whole simulation harness has exactly this one blocking primitive. A background thread
writes the reply after a short delay, standing in for the external responder."""

import json
import threading
import time

import pytest

from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir
from tests.eval.ChatConversation.simulation.exchange_transport import ExchangeTransport
from tests.unit.ExchangeTransport.fakes import Widget


class TestReplyPickup:
    def test_blocks_until_the_reply_file_is_written(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        transport = ExchangeTransport(exchange, "widget", timeout=5, poll_interval=0.01)
        reply_path = exchange.replies / "00001.json"
        delay = 0.15

        def respond_later():
            time.sleep(delay)
            reply_path.write_text(json.dumps({"value": 7}), encoding="utf-8")

        threading.Thread(target=respond_later, daemon=True).start()
        t0 = time.monotonic()
        result = transport.call(payload={"prompt": "x"}, reply_schema=Widget.model_json_schema(),
                                validator=Widget.model_validate)
        elapsed = time.monotonic() - t0

        assert result == Widget(value=7)
        assert elapsed >= delay

    def test_raises_timeout_error_when_never_answered(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        transport = ExchangeTransport(exchange, "widget", timeout=0.05, poll_interval=0.01)

        with pytest.raises(TimeoutError):
            transport.call(payload={"prompt": "x"}, reply_schema=Widget.model_json_schema(),
                           validator=Widget.model_validate)
