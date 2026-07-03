"""PendingRequest — one request written to `ExchangeDir.pending`, the contract a responder reads.

Written JSON shape: `{"seq": int, "kind": "pitch"|"analysis"|"intent"|"retry"|"agent",
...payload, "reply_schema": {...}}` — `payload` carries the FULL prompt text (`{"prompt": "..."}`
for the structured-output kinds) or, for `agent`, the full serialized message list plus the tool
JSON schema (`{"messages": [...], "tools": [...]}`). `reply_schema` is the JSON schema of the
expected reply (ChatReply / TurnAnalysis / SearchIntent / RetryDecision / AgentReply) so a
responder — human or model — knows exactly which fields to fill without reading any source code.
"""

import json
from pathlib import Path


class PendingRequest:
    def __init__(self, seq: int, kind: str, payload: dict, reply_schema: dict):
        self.seq = seq
        self.kind = kind
        self.payload = payload
        self.reply_schema = reply_schema

    def filename(self) -> str:
        return f"{self.seq:05d}-{self.kind}.json"

    def as_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, **self.payload,
                "reply_schema": self.reply_schema}

    def write(self, pending_dir: Path) -> Path:
        path = pending_dir / self.filename()
        path.write_text(json.dumps(self.as_dict(), ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return path
