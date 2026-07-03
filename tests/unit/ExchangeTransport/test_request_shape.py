"""The pending request written for one call carries the sequence id, the kind tag, the full
payload (e.g. the prompt) and the expected reply's JSON schema — everything an external
responder needs without reading any source code. Once answered, the SAME content is simply
relocated to `answered/` (never rewritten), so reading it there verifies the shape that was
written to `pending/` in the first place."""

import json

from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir
from tests.eval.ChatConversation.simulation.exchange_transport import ExchangeTransport
from tests.unit.ExchangeTransport.fakes import Widget


class TestRequestShape:
    def test_answered_request_carries_seq_kind_payload_and_schema(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        transport = ExchangeTransport(exchange, "widget", timeout=5, poll_interval=0.01)
        (exchange.replies / "00001.json").write_text(
            json.dumps({"value": 42}), encoding="utf-8")

        result = transport.call(payload={"prompt": "riformula il gioco ideale"},
                                reply_schema=Widget.model_json_schema(),
                                validator=Widget.model_validate)

        assert result == Widget(value=42)
        [answered] = list(exchange.answered.iterdir())
        assert answered.name == "00001-widget.json"
        written = json.loads(answered.read_text(encoding="utf-8"))
        assert written["seq"] == 1
        assert written["kind"] == "widget"
        assert written["prompt"] == "riformula il gioco ideale"
        assert written["reply_schema"] == Widget.model_json_schema()

    def test_pending_is_empty_once_answered(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        transport = ExchangeTransport(exchange, "widget", timeout=5, poll_interval=0.01)
        (exchange.replies / "00001.json").write_text(
            json.dumps({"value": 1}), encoding="utf-8")

        transport.call(payload={"prompt": "x"}, reply_schema=Widget.model_json_schema(),
                       validator=Widget.model_validate)

        assert list(exchange.pending.iterdir()) == []
