"""FileExchangeAgentLLM — the tool-calling LLM stand-in for the `agent` engine's simulation arm.

Implements the two-method contract `AgenticChat` needs from its `llm` (app/chat/agentic.py:54-63,
98-125): `.bind_tools(tools)` (records the LangChain tool(s) so their JSON schema rides every
request) and `.invoke(messages) -> AIMessage`, possibly carrying `tool_calls`. Each call
serializes the FULL message list (system/user/assistant/tool turns so far) plus the tool schemas
into one exchange request tagged `kind="agent"`, and maps the responder's `AgentReply`
(`{"tool_calls": [...]}` or `{"content": "..."}`, see agent_reply.py) onto a real `AIMessage` —
the exact shape `AgenticChat`'s loop already reads via `ai.tool_calls` (agentic.py:102), so no
engine code changes at all.

Note the loop's own semantics (unchanged, just worth restating here): the model's `content` on a
tool-calling round is never shown to the customer — the reply is generated afterwards by a
SEPARATE `pitch`-kind exchange (FileExchangeLLM feeding ChatAdvisor.pitch) over the union of
every tool result. A responder ending the loop with `{"content": "..."}` is just signalling "no
more searches needed"; the text itself is discarded.
"""

from langchain_core.messages import AIMessage, BaseMessage

from tests.eval.ChatConversation.simulation.agent_reply import AgentReply
from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir
from tests.eval.ChatConversation.simulation.exchange_transport import ExchangeTransport

_ROLE_BY_TYPE = {"system": "system", "human": "user", "ai": "assistant", "tool": "tool"}


class FileExchangeAgentLLM:
    def __init__(self, exchange: ExchangeDir, timeout: float = 900.0, poll_interval: float = 1.0):
        self.transport = ExchangeTransport(exchange, "agent", timeout=timeout,
                                           poll_interval=poll_interval)
        self._tools_schema: list[dict] = []

    def bind_tools(self, tools) -> "FileExchangeAgentLLM":
        self._tools_schema = [self._tool_schema(tool) for tool in tools]
        return self

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        reply: AgentReply = self.transport.call(
            payload={"messages": [self._serialize(m) for m in messages],
                     "tools": self._tools_schema},
            reply_schema=AgentReply.model_json_schema(),
            validator=AgentReply.model_validate,
        )
        tool_calls = [{"name": call.name, "args": call.args, "id": f"sim-{i}"}
                     for i, call in enumerate(reply.tool_calls, start=1)]
        return AIMessage(content=reply.content, tool_calls=tool_calls)

    @staticmethod
    def _serialize(message: BaseMessage) -> dict:
        entry = {"role": _ROLE_BY_TYPE.get(message.type, message.type), "content": message.content}
        tool_call_id = getattr(message, "tool_call_id", None)
        if tool_call_id is not None:
            entry["tool_call_id"] = tool_call_id
        if getattr(message, "tool_calls", None):
            entry["tool_calls"] = message.tool_calls
        return entry

    @staticmethod
    def _tool_schema(tool) -> dict:
        return {"name": tool.name, "description": tool.description,
                "parameters": tool.args_schema.model_json_schema() if tool.args_schema else {}}

    @property
    def calls(self) -> int:
        return self.transport.calls
