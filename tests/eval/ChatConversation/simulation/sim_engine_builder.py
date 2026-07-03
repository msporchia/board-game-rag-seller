"""SimEngineBuilder — assembles the chosen ChatConversation engine (pipeline/piloted/agent)
exactly like the real eval's `graph` fixture (tests/eval/ChatConversation/conftest.py), but with
every LLM role played by a FileExchange* stand-in instead of `ChatOllama`, so an external
responder answers in the model's place. Same frozen corpus + throwaway-collection recipe as the
real fixture, on a SIM-namespaced collection so a simulation run never collides with a
concurrently running real eval session; the collection is dropped on exit exactly like the real
fixture's teardown.
"""

import json
from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from app.chat.advisor import ChatAdvisor
from app.chat.models.analysis import TurnAnalysis
from app.chat.models.intent import SearchIntent
from app.chat.models.reply import ChatReply
from app.chat.models.retry import RetryDecision
from app.core.vector_store import GameVectorStore
from app.ingestion.serializer import DocumentSerializer
from app.models.game_doc import GameDoc
from app.rag.retriever import GameRetriever
from tests.eval.ChatConversation.simulation.exchange_dir import ExchangeDir
from tests.eval.ChatConversation.simulation.file_exchange_agent_llm import FileExchangeAgentLLM
from tests.eval.ChatConversation.simulation.file_exchange_llm import FileExchangeLLM
from tests.eval.ChatConversation.simulation.sim_usage_tracker import SimUsageTracker

FROZEN = (Path(__file__).resolve().parents[3] / "fixtures" / "suites" / "core"
          / "games_enriched.json")
COLLECTION = "games_eval_chat_conversation_sim"


class SimEngineBuilder:
    def __init__(self, exchange: ExchangeDir, timeout: float = 900.0):
        self.exchange = exchange
        self.timeout = timeout
        self.usage = SimUsageTracker()

    def _llm(self, kind: str, schema) -> FileExchangeLLM:
        llm = FileExchangeLLM(self.exchange, kind, schema, timeout=self.timeout)
        self.usage.track(llm)
        return llm

    @contextmanager
    def build(self, engine_name: str):
        """Index the frozen corpus on the throwaway collection, wire the chosen engine with
        FileExchange* LLMs, yield it, then drop the collection — same lifecycle as the real
        `graph` fixture's `try/finally`."""
        if not FROZEN.exists():
            raise SystemExit(f"frozen corpus missing at {FROZEN} — run: docker compose exec "
                             "seller-api python -m tests.eval.GameRetriever.freeze_corpus")
        composed = [GameDoc(**d) for d in json.loads(FROZEN.read_text(encoding="utf-8"))]
        documents = [DocumentSerializer().to_document(g) for g in composed]
        ids = [GameVectorStore.point_id(g.id_product) for g in composed]

        store = GameVectorStore(collection_name=COLLECTION)
        store.index(documents, ids=ids, recreate=True)
        try:
            advisor = ChatAdvisor(retriever=GameRetriever(store=store),
                                  llm=self._llm("pitch", ChatReply))
            if engine_name == "piloted":
                from app.chat.piloted import PilotedChat

                engine = PilotedChat(advisor=advisor,
                                     intent_llm=self._llm("intent", SearchIntent),
                                     retry_llm=self._llm("retry", RetryDecision),
                                     checkpointer=InMemorySaver())
            elif engine_name == "agent":
                from app.chat.agentic import AgenticChat

                agent_llm = FileExchangeAgentLLM(self.exchange, timeout=self.timeout)
                self.usage.track(agent_llm)
                engine = AgenticChat(advisor=advisor, llm=agent_llm)
            else:
                from app.chat.graph import ChatGraph

                engine = ChatGraph(advisor=advisor,
                                   analyze_llm=self._llm("analysis", TurnAnalysis),
                                   strong_llm=self._llm("pitch", ChatReply),
                                   checkpointer=InMemorySaver())
            yield engine
        finally:
            store.client.delete_collection(COLLECTION)
