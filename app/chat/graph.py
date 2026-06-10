"""ChatGraph — the stateful conversational layer (Phase 5, LangGraph).

A small StateGraph wrapped around the Phase 4 retrieve→pitch core (which stays in ChatAdvisor —
grounding validation, deterministic fallback and prompt assembly live in ONE place):

    START → analyze → route ──(conditional)──> retrieve → generate → END
                        └────────(skip)─────────────────────↑

- analyze   one structured-output LLM call per turn: reads the user (enthusiasm, decisiveness,
            expertise, reply style — docs/note.md) and proposes escalation (model tiering).
- route     DETERMINISTIC code (no second LLM call): applies the strategy transition rules from
            docs/note.md to the analyze output and keeps the exchanges-without-proposal counter.
- retrieve  parses quick-reply clicks into SearchFilters fragments merged into the session
            ("a click becomes a new filter"), then hybrid search via the existing GameRetriever.
- generate  delegates to ChatAdvisor.pitch — same grounded path as Phase 4, with the strategy
            and expertise shaping the prompt, and the strong model when analyze escalated.

The conditional edge decides whether this turn needs FRESH games: proposal strategies
(QUICK_MATCH, DISCOVERY), any turn with new clicks (new filters), or an empty table always
retrieve; a GUIDED/EXPLANATORY follow-up keeps talking over the games already on the table
instead of reshuffling the cards under the customer mid-guidance.

Why a checkpointer: LangGraph persists the full state after every node, keyed by `thread_id`
(= our `session_id`), so memory is a property of the graph runtime, not hand-rolled session
code — the API handler stays stateless. We use SqliteSaver on a local file under data/, next to
the enrichment DB (same local-first discipline). Swapping to production storage is the same
provider-swap as everywhere else in the project: construct `PostgresSaver`/`RedisSaver` (their
respective `langgraph-checkpoint-*` packages) instead of SqliteSaver and pass it to ChatGraph —
no node, state or API change.
"""

import sqlite3
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from app.chat.advisor import ChatAdvisor
from app.chat.choices import parse_choices
from app.chat.models import ChatReply, ChatResponse, Strategy, TurnAnalysis
from app.core.tracing import get_trace_callbacks
from app.config import settings
from app.core.logging import get_logger
from app.models import GameHit
from app.rag.filters import SearchFilters

log = get_logger(__name__)

# docs/note.md: "after max 3-4 exchanges without a concrete proposal → force QUICK MATCH".
FORCE_QUICK_MATCH_AFTER = 3

# How many games each strategy puts on the table (GUIDED: "massimo 1-2 scelte chiare";
# QUICK_MATCH: "3-4 giochi concreti").
_STRATEGY_K = {
    Strategy.GUIDED: 2,
    Strategy.EXPLANATORY: 3,
    Strategy.DISCOVERY: 5,
    Strategy.QUICK_MATCH: 4,
}

_HISTORY_MAX = 12  # rolling window of history entries kept in state (≈ 6 exchanges)


def _add_history(left: list | None, right: list | None) -> list:
    """History reducer: append new entries, keep a rolling window."""
    return ((left or []) + (right or []))[-_HISTORY_MAX:]


def _merge_filters(left: dict | None, right: dict | None) -> dict:
    """Filters reducer: per-field merge — the latest click on a dimension wins."""
    return {**(left or {}), **(right or {})}


class ChatState(TypedDict, total=False):
    """The conversation state LangGraph checkpoints per session.

    Channels without a reducer are last-value (each turn's input overwrites them); `history`
    and `filters_spec` have reducers so nodes contribute fragments and the runtime accumulates.
    `filters_spec` is kept as the plain `SearchFilters.from_dict` spec (JSON-friendly for the
    checkpointer); it becomes a real SearchFilters only at retrieval time.
    """

    # per-turn inputs
    message: str
    choices: list[str]
    k: int

    # rolling conversation memory
    history: Annotated[list[str], _add_history]      # "utente: ..." / "bot: ..." lines
    filters_spec: Annotated[dict, _merge_filters]    # accumulated SearchFilters spec

    # analyze output (user-analysis dimensions + escalation contract, docs/note.md)
    enthusiasm: str
    decisiveness: str
    expertise_level: str
    reply_style: str
    escalate: bool
    escalation_reason: str
    confidence: float

    # routing
    strategy: str
    turns_without_proposal: int

    # retrieval / generation
    hits: list[GameHit]              # the games currently "on the table"
    last_recommended_ids: list[int]  # ids featured in the last reply
    response: ChatResponse           # this turn's output


def pick_strategy(analysis: TurnAnalysis, turns_without_proposal: int) -> Strategy:
    """The strategy transition rules from docs/note.md, as deterministic code.

    Order matters — first match wins:
      1. >= FORCE_QUICK_MATCH_AFTER exchanges without a concrete proposal → forced QUICK_MATCH.
      2. Decided user → QUICK_MATCH ("vai velocemente a proporre quando l'utente è deciso").
      3. High enthusiasm → DISCOVERY, or EXPLANATORY for beginners (they need the mechanics
         explained before free-form exploration lands).
      4. Low enthusiasm or short replies → concrete and simple: QUICK_MATCH if the user already
         shows some decisiveness, otherwise GUIDED.
      5. Default → GUIDED (the safe stance for an undecided, middle-ground user).
    """
    if turns_without_proposal >= FORCE_QUICK_MATCH_AFTER:
        return Strategy.QUICK_MATCH
    if analysis.decisiveness == "decided":
        return Strategy.QUICK_MATCH
    if analysis.enthusiasm == "high":
        return Strategy.EXPLANATORY if analysis.expertise_level == "beginner" else Strategy.DISCOVERY
    if analysis.enthusiasm == "low" or analysis.reply_style == "short":
        return Strategy.QUICK_MATCH if analysis.decisiveness == "moderate" else Strategy.GUIDED
    return Strategy.GUIDED


def _analysis_prompt(history: list[str], message: str) -> str:
    """Italian like the other prompts; the output is constrained to TurnAnalysis."""
    conversation = "\n".join(history) if history else "(inizio conversazione)"
    return f"""Analizza il cliente di un negozio di giochi da tavolo a partire dalla conversazione.

CONVERSAZIONE FINORA:
{conversation}

ULTIMO MESSAGGIO DEL CLIENTE:
{message}

Valuta SOLO dal testo del cliente:
- enthusiasm: low/medium/high — quanto è coinvolto.
- decisiveness: undecided/moderate/decided — quanto ha le idee chiare su cosa vuole.
- expertise_level: beginner/intermediate/advanced — dai termini che usa (es. "worker placement"
  → advanced; "un gioco da fare in famiglia" senza termini tecnici → beginner).
- reply_style: short/long — lunghezza e ricchezza delle sue risposte.
- escalate: true SOLO se la conversazione è complessa o il cliente sembra pronto all'acquisto
  (budget, numero di giocatori, urgenza) e merita il modello più capace. Motiva in
  escalation_reason e indica la tua confidence (0-1)."""


class ChatGraph:
    """The compiled Phase 5 graph. One instance per process; sessions are thread_ids."""

    def __init__(self, advisor: ChatAdvisor | None = None, analyze_llm=None, strong_llm=None,
                 checkpointer=None):
        self.advisor = advisor or ChatAdvisor()
        # Analyzer: cheap, temperature 0 — classification, not prose. Tests inject a fake.
        self._analyze_llm = analyze_llm or ChatOllama(
            model=settings.llm_model, base_url=settings.ollama_url, temperature=0.0,
            callbacks=get_trace_callbacks("chat.analyze"),
        ).with_structured_output(TurnAnalysis)
        # Escalation target (model tiering, docs/note.md). Defaults to the same local model, so
        # the CONTRACT is exercised end-to-end as a no-op until a stronger model is configured.
        self._strong_model = settings.llm_model_strong or settings.llm_model
        self._strong_llm = strong_llm or ChatOllama(
            model=self._strong_model, base_url=settings.ollama_url, temperature=0.4,
            callbacks=get_trace_callbacks("chat.generate.strong"),
        ).with_structured_output(ChatReply)

        self._graph = self._build(checkpointer or _sqlite_checkpointer())

    # ---- graph wiring ----------------------------------------------------------

    def _build(self, checkpointer):
        builder = StateGraph(ChatState)
        builder.add_node("analyze", self._analyze)
        builder.add_node("route", self._route)
        builder.add_node("retrieve", self._retrieve)
        builder.add_node("generate", self._generate)

        builder.add_edge(START, "analyze")
        builder.add_edge("analyze", "route")
        builder.add_conditional_edges("route", self._needs_retrieval,
                                      {"retrieve": "retrieve", "generate": "generate"})
        builder.add_edge("retrieve", "generate")
        builder.add_edge("generate", END)
        return builder.compile(checkpointer=checkpointer)

    # ---- nodes -------------------------------------------------------------------

    def _analyze(self, state: ChatState) -> dict:
        """One structured LLM call reading the user; on failure keep the previous analysis."""
        message = state["message"]
        try:
            analysis: TurnAnalysis = self._analyze_llm.invoke(
                _analysis_prompt(state.get("history") or [], message))
        except Exception:  # noqa: BLE001 — the analysis failing must never kill the turn
            log.warning("analyze_llm_failed", fallback="previous_or_default_analysis")
            analysis = TurnAnalysis(
                enthusiasm=state.get("enthusiasm", "medium"),
                decisiveness=state.get("decisiveness", "undecided"),
                expertise_level=state.get("expertise_level", "beginner"),
                reply_style=state.get("reply_style", "short"),
            )
        log.info("analyze_done", enthusiasm=analysis.enthusiasm,
                 decisiveness=analysis.decisiveness, expertise=analysis.expertise_level,
                 style=analysis.reply_style, escalate=analysis.escalate)
        return {
            "enthusiasm": analysis.enthusiasm,
            "decisiveness": analysis.decisiveness,
            "expertise_level": analysis.expertise_level,
            "reply_style": analysis.reply_style,
            "escalate": analysis.escalate,
            "escalation_reason": analysis.escalation_reason,
            "confidence": analysis.confidence,
            "history": [f"utente: {message}"],
        }

    def _route(self, state: ChatState) -> dict:
        """Deterministic strategy routing (docs/note.md transition rules) + the stall counter.

        A "concrete proposal" is a proposal-strategy turn (QUICK_MATCH / DISCOVERY: fresh
        retrieval, multi-game pitch); GUIDED/EXPLANATORY turns guide and explain over examples,
        so they increment the counter that eventually forces QUICK_MATCH.
        """
        analysis = TurnAnalysis(
            enthusiasm=state.get("enthusiasm", "medium"),
            decisiveness=state.get("decisiveness", "undecided"),
            expertise_level=state.get("expertise_level", "beginner"),
            reply_style=state.get("reply_style", "short"),
        )
        stalled = state.get("turns_without_proposal", 0)
        strategy = pick_strategy(analysis, stalled)
        proposal = strategy in (Strategy.QUICK_MATCH, Strategy.DISCOVERY)
        log.info("route_done", strategy=strategy.value, turns_without_proposal=stalled)
        return {
            "strategy": strategy.value,
            "turns_without_proposal": 0 if proposal else stalled + 1,
        }

    def _needs_retrieval(self, state: ChatState) -> str:
        """Conditional edge: does this turn need FRESH games on the table?"""
        if state.get("strategy") in (Strategy.QUICK_MATCH.value, Strategy.DISCOVERY.value):
            return "retrieve"  # proposal strategies always work over fresh, filtered hits
        if state.get("choices"):
            return "retrieve"  # a click is a new filter → re-search with it
        if not state.get("hits"):
            return "retrieve"  # nothing on the table yet (first turn)
        return "generate"      # keep guiding/explaining over the games already shown

    def _retrieve(self, state: ChatState) -> dict:
        """Clicks → SearchFilters fragments (merged into the session), then hybrid search."""
        fragment, leftovers = parse_choices(state.get("choices"))
        spec = _merge_filters(state.get("filters_spec"), fragment)
        filters = SearchFilters.from_dict(spec) if spec else None

        # Query: previous user turns give context the current message may lack (e.g. the forced
        # QUICK_MATCH after a guided exchange must search with everything collected so far).
        history = state.get("history") or []
        user_turns = [h[len("utente: "):] for h in history if h.startswith("utente: ")]
        previous = user_turns[:-1][-2:]  # up to 2 turns before the current one
        query = "\n".join([*previous, state["message"], *leftovers])

        # The strategy decides how many games go on the table (GUIDED shows 1-2, QUICK_MATCH
        # 3-4); only free-form DISCOVERY honors the request's k.
        strategy = Strategy(state["strategy"])
        k = (state.get("k") or 5) if strategy is Strategy.DISCOVERY else _STRATEGY_K[strategy]
        hits = self.advisor.retriever.search(query, k=k, filters=filters)
        log.info("retrieve_done", k=k, filters=sorted(spec) or None, hits=len(hits))
        return {"hits": hits, "filters_spec": fragment}

    def _generate(self, state: ChatState) -> dict:
        """Delegate to the Phase 4 grounded pitch; strategy/expertise shape the prompt."""
        llm = None
        if state.get("escalate"):
            log.info("generate_escalating", model=self._strong_model,
                     reason=state.get("escalation_reason") or "n/a",
                     confidence=round(state.get("confidence") or 0.0, 2))
            llm = self._strong_llm

        history = state.get("history") or []
        response = self.advisor.pitch(
            state["message"], state.get("hits") or [],
            strategy=state.get("strategy"),
            expertise_level=state.get("expertise_level"),
            history="\n".join(history[:-1]) or None,  # [:-1] = exchanges before this turn
            llm=llm,
        )
        return {
            "response": response,
            "last_recommended_ids": [g.id_product for g in response.games],
            "history": [f"bot: {response.message}"],
        }

    # ---- API ---------------------------------------------------------------------

    def reply(self, message: str, choices: list[str] | None = None, k: int = 5,
              session_id: str = "default") -> ChatResponse:
        """One stateful turn. Same return contract as ChatAdvisor.reply (Phase 4)."""
        out = self._graph.invoke(
            {"message": message, "choices": choices or [], "k": k},
            config={"configurable": {"thread_id": session_id}},
        )
        return out["response"]

    def state(self, session_id: str) -> dict:
        """The checkpointed state of a session (debugging/tests)."""
        snapshot = self._graph.get_state({"configurable": {"thread_id": session_id}})
        return snapshot.values


def _sqlite_checkpointer():
    """Default session storage: SqliteSaver on a local file under data/ (next to seller.db).

    `check_same_thread=False` because FastAPI serves sync handlers from a threadpool; SqliteSaver
    serializes access internally. Tests pass an InMemorySaver instead; production would pass a
    PostgresSaver/RedisSaver — the graph does not care (see module docstring).
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    path = Path(settings.chat_checkpoint_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver(sqlite3.connect(str(path), check_same_thread=False))
