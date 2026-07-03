"""FileExchangeAgentLLM — maps the responder's `AgentReply` onto a real `AIMessage`, the exact
shape `AgenticChat`'s loop reads via `ai.tool_calls` (app/chat/agentic.py:102-125). Covers both
accepted reply shapes: a tool call that must keep the loop going, and a final answer that must
end it (empty `tool_calls`)."""

import json
import threading
import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.chat.tools.search_catalog import SearchCatalogTool
from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir
from tests.eval.ChatConversation.simulation.file_exchange_agent_llm import FileExchangeAgentLLM


def _respond_after(reply_path, payload, delay=0.05):
    def respond():
        time.sleep(delay)
        reply_path.write_text(json.dumps(payload), encoding="utf-8")
    threading.Thread(target=respond, daemon=True).start()


class TestToolCalls:
    def test_tool_calls_reply_maps_to_an_aimessage_with_tool_calls(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        llm = FileExchangeAgentLLM(exchange, timeout=5, poll_interval=0.01)
        llm.bind_tools([SearchCatalogTool().as_tool()])
        _respond_after(exchange.replies / "00001.json", {
            "tool_calls": [{"name": "search_catalog",
                           "args": {"query": "cooperativo", "players": 2}}],
        })

        ai = llm.invoke([SystemMessage(content="sys"), HumanMessage(content="ciao")])

        # AIMessage normalizes each tool call, adding "type": "tool_call".
        assert ai.tool_calls == [
            {"name": "search_catalog", "args": {"query": "cooperativo", "players": 2},
             "id": "sim-1", "type": "tool_call"}]
        assert ai.content == ""

    def test_content_only_reply_ends_the_loop_with_no_tool_calls(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        llm = FileExchangeAgentLLM(exchange, timeout=5, poll_interval=0.01)
        llm.bind_tools([SearchCatalogTool().as_tool()])
        _respond_after(exchange.replies / "00001.json", {"content": "ho trovato abbastanza"})

        ai = llm.invoke([HumanMessage(content="ciao")])

        assert ai.tool_calls == []
        assert ai.content == "ho trovato abbastanza"

    def test_request_carries_serialized_messages_and_tool_schema(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        llm = FileExchangeAgentLLM(exchange, timeout=5, poll_interval=0.01)
        llm.bind_tools([SearchCatalogTool().as_tool()])
        (exchange.replies / "00001.json").write_text(
            json.dumps({"content": "ok"}), encoding="utf-8")

        llm.invoke([SystemMessage(content="istruzioni"), HumanMessage(content="un gioco corto")])

        [answered] = list(exchange.answered.iterdir())
        written = json.loads(answered.read_text(encoding="utf-8"))
        assert written["kind"] == "agent"
        assert written["messages"] == [
            {"role": "system", "content": "istruzioni"},
            {"role": "user", "content": "un gioco corto"},
        ]
        assert written["tools"][0]["name"] == "search_catalog"
        assert "properties" in written["tools"][0]["parameters"]
