"""FileExchangeLLM — a structured-output LLM stand-in for the strong-model simulation harness.

Drop-in replacement for the `.invoke(prompt) -> <pydantic model>` contract every non-agent chat
collaborator expects of its injected `llm`:
  - `ChatAdvisor(llm=...)` — `ChatReply` (app/chat/advisor.py:54-64)
  - `TurnAnalyzer(llm=...)` — `TurnAnalysis` (app/chat/analyzer.py:21-26)
  - `PilotedChat(intent_llm=..., retry_llm=...)` — `SearchIntent` / `RetryDecision`
    (app/chat/piloted.py:62-74)

Each call round-trips through the exchange directory instead of Ollama (`ExchangeTransport`
owns the write/poll/validate/reject mechanics — see its module docstring for the protocol): an
external responder answers on the EXACT SAME prompt and schema production code would send,
tagged with `kind` so the responder knows which shape to fill.
"""

from pydantic import BaseModel

from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir
from tests.eval.ChatConversation.simulation.exchange_transport import ExchangeTransport


class FileExchangeLLM:
    def __init__(self, exchange: ExchangeDir, kind: str, schema: type[BaseModel],
                timeout: float = 900.0, poll_interval: float = 1.0):
        self.kind = kind
        self.schema = schema
        self.transport = ExchangeTransport(exchange, kind, timeout=timeout,
                                           poll_interval=poll_interval)

    def invoke(self, prompt: str):
        return self.transport.call(
            payload={"prompt": prompt},
            reply_schema=self.schema.model_json_schema(),
            validator=self.schema.model_validate,
        )

    @property
    def calls(self) -> int:
        return self.transport.calls
