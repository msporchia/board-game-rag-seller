"""ExchangeDir — the file layout of one simulation exchange directory.

The seam between the process running the chat engine (inside the container, `simulation/run.py`)
and an external responder (a human or another model, on the host): everything either side needs
to agree on lives under one root —

    <root>/pending/<seq>-<kind>.json    one JSON request per LLM call, `seq` zero-padded
    <root>/replies/<seq>.json           where the responder drops its answer
    <root>/rejected/<seq>-<attempt>.json  a reply that failed validation, moved here so the
                                          responder can see WHY (sibling `.error.txt`) and retry
    <root>/answered/<seq>-<kind>.json   the pending request, moved here once its reply validated
                                          — so "answer everything left in pending/" is always the
                                          right instruction, nothing to track by hand.

One `ExchangeDir` instance (and its `next_seq()` counter) is shared by every FileExchangeLLM /
FileExchangeAgentLLM in a run, so sequence ids are globally monotonic across pitch / analysis /
intent / retry / agent calls, in the order they actually happened — a responder reads `pending/`
in file order without needing to track per-kind counters. `docker-compose.yml` bind-mounts the
whole repo at `/app` (`.:/app`), so a root under `./data` on the host is `/app/data` in the
container without any extra plumbing.
"""

import os
from pathlib import Path


class ExchangeDir:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.pending = self.root / "pending"
        self.replies = self.root / "replies"
        self.rejected = self.root / "rejected"
        self.answered = self.root / "answered"
        # The runner lives INSIDE the container (root), the responder is on the HOST (its own
        # uid) — the whole point of the exchange dir is that both sides can write here (the
        # runner writes pending/*, the responder writes replies/*), so every directory is made
        # world-writable rather than left at the container's default umask, which would leave a
        # host process unable to drop a reply file at all.
        for directory in (self.root, self.pending, self.replies, self.rejected, self.answered):
            directory.mkdir(parents=True, exist_ok=True)
            os.chmod(directory, 0o777)
        self._next = self._resume_from()

    def _resume_from(self) -> int:
        """Resume one above the highest sequence id already present anywhere under the root, so
        re-running against a non-empty exchange directory (e.g. a restarted runner) never reuses
        a sequence id a responder already answered or rejected."""
        seen = []
        for directory in (self.pending, self.replies, self.answered, self.rejected):
            for path in directory.iterdir():
                head = path.name.split("-", 1)[0].split(".", 1)[0]
                if head.isdigit():
                    seen.append(int(head))
        return (max(seen) + 1) if seen else 1

    def next_seq(self) -> int:
        seq = self._next
        self._next += 1
        return seq
