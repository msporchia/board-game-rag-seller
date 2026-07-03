"""SimUsageTracker — the `llm_usage` interface `ConversationDriver` expects, over FileExchange*
stand-ins instead of a LangChain callback (`LLMUsageTracker`, tests/eval/ChatConversation/
usage.py).

Every completed round trip on a tracked FileExchangeLLM / FileExchangeAgentLLM is one "LLM
call" — the human (or model) responder answering one prompt — the direct analogue of
`LLMUsageTracker.llm_calls`. Token counts are always zero: a human-authored reply has no Ollama
token usage to report, and inventing a number would misrepresent the cost side of the
quality-vs-cost comparison rather than just omitting it (see `simulation/compare.py`).
"""


class SimUsageTracker:
    def __init__(self):
        self._tracked: list = []

    def track(self, llm) -> None:
        """Register a FileExchangeLLM / FileExchangeAgentLLM (anything with a `.calls` int)."""
        self._tracked.append(llm)

    def snapshot(self) -> dict:
        return {"llm_calls": sum(llm.calls for llm in self._tracked),
                "tokens_in": 0, "tokens_out": 0}

    def delta_since(self, before: dict) -> dict:
        return {key: value - before[key] for key, value in self.snapshot().items()}
