"""TurnAnalyzer — the "read the customer" step, separated from the graph topology.

One structured LLM call per turn → `TurnAnalysis` (the four user-analysis dimensions + the
escalation contract, docs/note.md). Extracted from `ChatGraph` so the graph stays orchestration:
its analyze node delegates here, exactly like route → `routing`, generate → `ChatAdvisor`,
retrieve → `GameRetriever`. The prompt lives in `app/chat/prompts.py` (`ANALYSIS`).
"""

from langchain_ollama import ChatOllama

from app.chat import prompts
from app.chat.models.analysis import TurnAnalysis
from app.config import settings
from app.core.logging import get_logger
from app.core.tracing.callbacks import get_trace_callbacks

log = get_logger(__name__)


class TurnAnalyzer:
    def __init__(self, llm=None):
        # Cheap, temperature 0 — classification, not prose. Tests inject a fake.
        self._llm = llm or ChatOllama(
            model=settings.llm_model, base_url=settings.ollama_url, temperature=0.0,
            callbacks=get_trace_callbacks("chat.analyze"),
        ).with_structured_output(TurnAnalysis)

    @staticmethod
    def prompt(history: list[str], message: str) -> str:
        conversation = "\n".join(history) if history else "(inizio conversazione)"
        return prompts.ANALYSIS.format(conversation=conversation, message=message)

    def analyze(self, history: list[str] | None, message: str,
                fallback: TurnAnalysis) -> TurnAnalysis:
        """One structured call reading the user; on failure return `fallback` (the previous
        analysis), so a transient analyzer failure never kills the turn."""
        try:
            return self._llm.invoke(self.prompt(history or [], message))
        except Exception:  # noqa: BLE001 — the analysis failing must never kill the turn
            log.warning("analyze_llm_failed", fallback="previous_or_default_analysis")
            return fallback
