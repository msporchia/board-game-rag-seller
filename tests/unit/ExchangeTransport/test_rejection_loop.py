"""An invalid reply must NEVER crash the run or silently degrade to a default — it is archived
to `rejected/` with its validation error, and the transport keeps waiting at the same
`replies/<seq>.json` path for a corrected one. Only a reply that actually validates is accepted
and moves the pending request to `answered/`."""

import json
import threading
import time

from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir
from tests.eval.ChatConversation.simulation.exchange_transport import ExchangeTransport
from tests.unit.ExchangeTransport.fakes import Widget


class TestRejectionLoop:
    def test_invalid_reply_is_archived_and_a_corrected_one_is_accepted(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        transport = ExchangeTransport(exchange, "widget", timeout=5, poll_interval=0.01)
        reply_path = exchange.replies / "00001.json"
        # Not a valid Widget: "value" must be an int.
        reply_path.write_text(json.dumps({"value": "not-an-int"}), encoding="utf-8")

        def correct_it_later():
            time.sleep(0.1)
            reply_path.write_text(json.dumps({"value": 9}), encoding="utf-8")

        threading.Thread(target=correct_it_later, daemon=True).start()
        result = transport.call(payload={"prompt": "x"}, reply_schema=Widget.model_json_schema(),
                                validator=Widget.model_validate)

        assert result == Widget(value=9)
        rejected = list(exchange.rejected.iterdir())
        rejected_json = [p for p in rejected if p.suffix == ".json"]
        rejected_errors = [p for p in rejected if p.name.endswith(".error.txt")]
        assert [p.name for p in rejected_json] == ["00001-1.json"]
        assert json.loads(rejected_json[0].read_text(encoding="utf-8")) == {"value": "not-an-int"}
        assert len(rejected_errors) == 1 and rejected_errors[0].read_text(encoding="utf-8")

    def test_never_leaves_a_stale_reply_file_at_the_seq_path(self, tmp_path):
        """After a reject the bad file is MOVED away, so the same path is free for a retry."""
        exchange = ExchangeDir(tmp_path)
        transport = ExchangeTransport(exchange, "widget", timeout=5, poll_interval=0.01)
        reply_path = exchange.replies / "00001.json"
        reply_path.write_text(json.dumps({"value": "bad"}), encoding="utf-8")

        def correct_it_later():
            time.sleep(0.1)
            reply_path.write_text(json.dumps({"value": 1}), encoding="utf-8")

        threading.Thread(target=correct_it_later, daemon=True).start()
        transport.call(payload={"prompt": "x"}, reply_schema=Widget.model_json_schema(),
                       validator=Widget.model_validate)

        # The final, accepted reply file is the one left at replies/ — no stray bad copy.
        assert [p.name for p in exchange.replies.iterdir()] == ["00001.json"]
        assert json.loads(reply_path.read_text(encoding="utf-8")) == {"value": 1}
