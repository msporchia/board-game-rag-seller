"""FileExchangeLLM — the `.invoke(prompt) -> <pydantic model>` contract ChatAdvisor/TurnAnalyzer/
PilotedChat expect of an injected `llm` (see its module docstring), played by an external
responder through the exchange directory instead of Ollama."""

import json
import threading
import time

import pytest

from app.chat.models.reply import ChatReply
from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir
from tests.eval.ChatConversation.simulation.file_exchange_llm import FileExchangeLLM


class TestInvoke:
    def test_invoke_returns_the_validated_schema_instance(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        llm = FileExchangeLLM(exchange, "pitch", ChatReply, timeout=5, poll_interval=0.01)

        def respond():
            time.sleep(0.05)
            (exchange.replies / "00001.json").write_text(json.dumps({
                "intro": "Eccone due!",
                "recommendations": [{"id": 34, "pitch": "Carcassonne è perfetto."}],
                "quick_replies": ["per 2 giocatori"],
            }), encoding="utf-8")

        threading.Thread(target=respond, daemon=True).start()
        reply = llm.invoke("RICHIESTA DEL CLIENTE:\nCerco un gioco di piazzamento tessere.")

        assert isinstance(reply, ChatReply)
        assert reply.recommendations[0].id == 34
        assert llm.calls == 1

    def test_request_is_tagged_pitch_and_carries_the_full_prompt(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        llm = FileExchangeLLM(exchange, "pitch", ChatReply, timeout=5, poll_interval=0.01)
        (exchange.replies / "00001.json").write_text(json.dumps({
            "intro": "", "recommendations": [], "quick_replies": [],
        }), encoding="utf-8")

        llm.invoke("un prompt qualsiasi, per intero")

        [answered] = list(exchange.answered.iterdir())
        written = json.loads(answered.read_text(encoding="utf-8"))
        assert written["kind"] == "pitch"
        assert written["prompt"] == "un prompt qualsiasi, per intero"
        assert "recommendations" in written["reply_schema"]["properties"]

    def test_invalid_reply_keeps_waiting_instead_of_raising_or_degrading(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        llm = FileExchangeLLM(exchange, "pitch", ChatReply, timeout=5, poll_interval=0.01)
        reply_path = exchange.replies / "00001.json"
        reply_path.write_text(json.dumps({"recommendations": "not-a-list"}), encoding="utf-8")

        def correct_it_later():
            time.sleep(0.1)
            reply_path.write_text(json.dumps({
                "intro": "ok", "recommendations": [], "quick_replies": [],
            }), encoding="utf-8")

        threading.Thread(target=correct_it_later, daemon=True).start()
        reply = llm.invoke("prompt")

        assert reply.intro == "ok"
        assert any(p.suffix == ".json" for p in exchange.rejected.iterdir())

    def test_timeout_raises_rather_than_hangs_forever(self, tmp_path):
        exchange = ExchangeDir(tmp_path)
        llm = FileExchangeLLM(exchange, "pitch", ChatReply, timeout=0.05, poll_interval=0.01)

        with pytest.raises(TimeoutError):
            llm.invoke("prompt")
