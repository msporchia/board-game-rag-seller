"""ReplyWaiter — blocks polling for one reply file, the only blocking primitive in the whole
simulation harness (every FileExchangeLLM / FileExchangeAgentLLM call goes through it).

Polls every `poll_interval` seconds; raises `TimeoutError` if nothing valid-JSON shows up within
`timeout` seconds — the harness must fail loudly rather than hang forever or silently degrade
(a degraded reply would pollute the very measurement this exists to produce). A reply file that
exists but does not yet parse (the responder may still be mid-write) is treated as "not there
yet" rather than a validation failure.
"""

import json
import time
from pathlib import Path


class ReplyWaiter:
    def __init__(self, poll_interval: float = 1.0, timeout: float = 900.0):
        self.poll_interval = poll_interval
        self.timeout = timeout

    def wait(self, reply_path: Path) -> dict:
        deadline = time.monotonic() + self.timeout
        while True:
            if reply_path.exists():
                try:
                    return json.loads(reply_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    pass  # mid-write race — try again next poll
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"no reply at {reply_path} after {self.timeout:.0f}s — "
                    "the responder never answered (or the reply file never parsed as JSON)")
            time.sleep(self.poll_interval)
