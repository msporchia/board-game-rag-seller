"""ExchangeTransport — the request/reply/validate/reject cycle shared by every FileExchange*
LLM stand-in (FileExchangeLLM, FileExchangeAgentLLM): one call is one round trip.

    write pending request → block for a reply → validate it → either
        (a) invalid: archive the bad reply to `rejected/<seq>-<attempt>.json` (+ sibling
            `.error.txt`) and keep waiting at the SAME `replies/<seq>.json` path for a
            corrected one — never falls back to a default value, because a silently degraded
            reply would pollute the measurement this harness exists to produce; or
        (b) valid: move the pending request to `answered/` and return the validated object.

`calls` counts completed (validated) round trips — the simulation's "LLM calls" cost, the
analogue of `LLMUsageTracker.llm_calls` (tests/eval/ChatConversation/usage.py) for a run with no
real LLM in the loop.
"""

import json
from pathlib import Path
from typing import Callable

from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir
from tests.eval.ChatConversation.simulation.pending_request import PendingRequest
from tests.eval.ChatConversation.simulation.reply_waiter import ReplyWaiter


class ExchangeTransport:
    def __init__(self, exchange: ExchangeDir, kind: str, timeout: float = 900.0,
                poll_interval: float = 1.0):
        self.exchange = exchange
        self.kind = kind
        self.waiter = ReplyWaiter(poll_interval=poll_interval, timeout=timeout)
        self.calls = 0

    def call(self, payload: dict, reply_schema: dict, validator: Callable[[dict], object]):
        seq = self.exchange.next_seq()
        request = PendingRequest(seq, self.kind, payload, reply_schema)
        pending_path = request.write(self.exchange.pending)
        reply_path = self.exchange.replies / f"{seq:05d}.json"

        attempt = 0
        while True:
            attempt += 1
            raw = self.waiter.wait(reply_path)
            try:
                result = validator(raw)
            except Exception as exc:  # noqa: BLE001 — any bad reply means "ask again", not crash
                self._reject(seq, attempt, reply_path, exc)
                continue
            break

        pending_path.replace(self.exchange.answered / pending_path.name)
        self.calls += 1
        return result

    def _reject(self, seq: int, attempt: int, reply_path: Path, exc: Exception) -> None:
        dest = self.exchange.rejected / f"{seq:05d}-{attempt}.json"
        reply_path.replace(dest)  # the bad reply itself, moved (not copied) out of replies/
        dest.with_suffix(".error.txt").write_text(str(exc), encoding="utf-8")
