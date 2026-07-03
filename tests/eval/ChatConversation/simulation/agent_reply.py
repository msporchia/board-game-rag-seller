"""AgentReply — the responder's reply shape for the `agent` kind (the `AgenticChat` tool loop,
app/chat/agentic.py:98-125), mapped onto a real `AIMessage` by `FileExchangeAgentLLM`.

Two accepted shapes, either or both fields present:
  - `{"tool_calls": [{"name": "search_catalog", "args": {...}}]}` — keep the tool loop going;
    `args` are the `SearchIntent` fields (query/players/max_minutes/youngest_player_age/
    cooperative), matching what `AgenticChat` already passes to `tool.run(**call["args"])`.
  - `{"content": "..."}` with no (or empty) `tool_calls` — end the loop; `AgenticChat` then
    generates the customer-facing reply itself via a separate `pitch` exchange over the union of
    everything the tool returned, so `content` here need not be the final answer (it never is —
    see the module docstring of `file_exchange_agent_llm.py`).
"""

from pydantic import BaseModel, Field


class AgentToolCall(BaseModel):
    """One requested `search_catalog` call. Private to `AgentReply` — nothing outside this
    module needs it on its own."""

    name: str = "search_catalog"
    args: dict = Field(default_factory=dict)


class AgentReply(BaseModel):
    content: str = ""
    tool_calls: list[AgentToolCall] = Field(default_factory=list)
