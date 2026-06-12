"""LLMUsageTracker — the cost denominator of the conversation eval (docs/idee.md §Q).

A LangChain callback handler attached to EVERY real model the engine under eval uses (analyze,
pitch, strong, intent, retry — whatever the arm wires): it counts LLM calls and accumulates
Ollama's token usage (`prompt_eval_count`/`eval_count`, surfaced by langchain-ollama as
`usage_metadata.input_tokens/output_tokens`). Tests snapshot it around each conversation, so
RESULTS can put Δquality next to Δcost when comparing engine arms.
"""

from langchain_core.callbacks import BaseCallbackHandler


class LLMUsageTracker(BaseCallbackHandler):
    def __init__(self):
        self.llm_calls = 0
        self.tokens_in = 0
        self.tokens_out = 0

    def on_llm_end(self, response, **kwargs) -> None:
        self.llm_calls += 1
        for generations in response.generations:
            for generation in generations:
                usage = getattr(getattr(generation, "message", None),
                                "usage_metadata", None) or {}
                self.tokens_in += usage.get("input_tokens", 0)
                self.tokens_out += usage.get("output_tokens", 0)

    def snapshot(self) -> dict:
        return {"llm_calls": self.llm_calls,
                "tokens_in": self.tokens_in,
                "tokens_out": self.tokens_out}

    def delta_since(self, before: dict) -> dict:
        return {key: value - before[key] for key, value in self.snapshot().items()}
