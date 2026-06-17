"""ChatGraph — the stateful conversational layer (Phase 5, LangGraph).

A small StateGraph wrapped around the Phase 4 retrieve→pitch core (which stays in ChatAdvisor —
grounding validation, deterministic fallback and prompt assembly live in ONE place):

    START → analyze → route ──(conditional)──> retrieve → generate → END
                        └────────(skip)─────────────────────↑

- analyze   one structured-output LLM call per turn: reads the user (enthusiasm, decisiveness,
            expertise, reply style — docs/note.md) and proposes escalation (model tiering).
- route     DETERMINISTIC code (no second LLM call): applies the strategy transition rules from
            docs/note.md (see `routing.pick_strategy`) to the analyze output and keeps the
            exchanges-without-proposal counter.
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
code — the API handler stays stateless. Default is SqliteSaver on a local file under data/
(see `checkpointer.sqlite_checkpointer`); swapping to production storage is the same
provider-swap as everywhere else in the project: construct `PostgresSaver`/`RedisSaver` (their
respective `langgraph-checkpoint-*` packages) instead and pass it to ChatGraph — no node,
state or API change.
"""

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from app.chat.advisor import ChatAdvisor
from app.chat.checkpointer import sqlite_checkpointer
from app.chat.choices import parse_choices
from app.chat.models.analysis import TurnAnalysis
from app.chat.models.reply import ChatReply
from app.chat.models.response import ChatResponse
from app.chat.models.strategy import Strategy
from app.chat.policies.generation_context import GenerationContext
from app.chat.policies.policy_set import PolicySet
from app.chat.policies.retrieval_context import RetrievalContext
from app.chat.routing import STRATEGY_K, pick_strategy
from app.chat.state import ChatState, merge_filters
from app.config import settings
from app.core.logging import get_logger
from app.core.tracing.callbacks import get_trace_callbacks

log = get_logger(__name__)


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

        self._graph = self._build(checkpointer or sqlite_checkpointer())

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

    @staticmethod
    def _analysis_prompt(history: list[str], message: str) -> str:
        """Italian like the other prompts; the output is constrained to TurnAnalysis."""
        conversation = "\n".join(history) if history else "(inizio conversazione)"
        return f"""Analizza il cliente di un negozio di giochi da tavolo a partire dalla conversazione.

CONVERSAZIONE FINORA:
{conversation}

ULTIMO MESSAGGIO DEL CLIENTE:
{message}

Hai DUE compiti, entrambi obbligatori: (1) profilare il cliente su quattro dimensioni;
(2) decidere se questo turno va escalato al modello più capace. Compila TUTTI i campi.

Valuta SOLO dal testo del cliente:
- enthusiasm: low/medium/high — quanto è coinvolto.
- decisiveness: undecided/moderate/decided — quanto ha le idee chiare su COSA comprare:
  - decided: ha scelto un titolo preciso e agisce: chiede se c'è, lo compra, lo prenota.
    Chiedere disponibilità o prezzo di un titolo specifico È decided, non un dubbio.
  - moderate: sa in parte cosa vuole. Due forme tipiche: vincoli concreti (giocatori, budget,
    durata) ma nessun titolo; oppure un titolo o un'opzione preferita ma con un dubbio residuo
    (andrà bene per noi? quale edizione? prima voglio saperne di più).
  - undecided: nessun criterio concreto: vago, si affida del tutto al negozio, non sa da dove
    partire.
  Attenzione a non sottostimare: chi esprime una preferenza o vincoli concreti NON è undecided;
  chi ha già scelto il titolo NON è moderate solo perché fa una domanda.
- expertise_level: beginner/intermediate/advanced — dal vocabolario: beginner = registro
  quotidiano, nessun termine tecnico (citare un titolo famoso senza capirlo non alza il
  livello); intermediate = conosce i classici introduttivi, termini di categoria usati in modo
  generico, meccaniche descritte a parole sue; advanced = gergo da hobbista preciso (nomi di
  meccaniche come "worker placement", giudizi di peso/complessità, la propria collezione).
- reply_style: short/long — lunghezza e ricchezza delle sue risposte.
- escalate: true/false — serve il modello più capace per rispondere a QUESTO turno?
  Metti true se l'ultimo messaggio contiene ALMENO UNO di questi segnali:
  - vincoli d'acquisto concreti dichiarati (budget in euro, numero di giocatori, una
    scadenza o urgenza);
  - intenzione esplicita di comprare ora, prenotare, o scegliere quale comprare tra le
    opzioni proposte;
  - un confronto tra più titoli con più vincoli incrociati (giocatori, durata, prezzo).
  Questi segnali valgono anche se compaiono già nel primissimo messaggio.
  Metti false per curiosità generica, chiacchiere, navigazione senza impegno, o cifre citate
  solo come ipotesi futura senza intenzione di comprare.
  Compila SEMPRE escalation_reason (una frase) e confidence (0-1), anche con escalate=false."""

    def _analyze(self, state: ChatState) -> dict:
        """One structured LLM call reading the user; on failure keep the previous analysis."""
        message = state["message"]
        policies = PolicySet.from_names(state.get("custom_policy"))
        try:
            analysis: TurnAnalysis = self._analyze_llm.invoke(
                self._analysis_prompt(state.get("history") or [], message))
        except Exception:  # noqa: BLE001 — the analysis failing must never kill the turn
            log.warning("analyze_llm_failed", fallback="previous_or_default_analysis")
            analysis = TurnAnalysis(
                enthusiasm=state.get("enthusiasm", "medium"),
                decisiveness=state.get("decisiveness", "undecided"),
                expertise_level=state.get("expertise_level", "beginner"),
                reply_style=state.get("reply_style", "short"),
            )
        expertise = policies.force_expertise(analysis.expertise_level)
        log.info("analyze_done", enthusiasm=analysis.enthusiasm,
                 decisiveness=analysis.decisiveness, expertise=expertise,
                 style=analysis.reply_style, escalate=analysis.escalate,
                 policies=policies.names)
        return {
            "enthusiasm": analysis.enthusiasm,
            "decisiveness": analysis.decisiveness,
            "expertise_level": expertise,
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
        policies = PolicySet.from_names(state.get("custom_policy"))
        strategy = policies.force_strategy(pick_strategy(analysis, stalled))
        proposal = strategy in (Strategy.QUICK_MATCH, Strategy.DISCOVERY)
        log.info("route_done", strategy=strategy.value, turns_without_proposal=stalled,
                 policies=policies.names)
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
        """Clicks → SearchFilters fragments (merged into the session), then hybrid search.

        The fetch runs through the policy chain (RetrievalContext): a policy may reshape the
        query/filters or reorder the hits before they reach the table.
        """
        fragment, leftovers = parse_choices(state.get("choices"))
        spec = merge_filters(state.get("filters_spec"), fragment)

        # Query: previous user turns give context the current message may lack (e.g. the forced
        # QUICK_MATCH after a guided exchange must search with everything collected so far).
        history = state.get("history") or []
        user_turns = [h[len("utente: "):] for h in history if h.startswith("utente: ")]
        previous = user_turns[:-1][-2:]  # up to 2 turns before the current one
        query = "\n".join([*previous, state["message"], *leftovers])

        # The strategy decides how many games go on the table (GUIDED shows 1-2, QUICK_MATCH
        # 3-4); only free-form DISCOVERY honors the request's k.
        strategy = Strategy(state["strategy"])
        k = (state.get("k") or 5) if strategy is Strategy.DISCOVERY else STRATEGY_K[strategy]
        policies = PolicySet.from_names(state.get("custom_policy"))
        rctx = RetrievalContext(query=query, k=k, retriever=self.advisor.retriever,
                                filters_spec=spec)
        hits = policies.run_retrieve(rctx, lambda c: c.execute())
        log.info("retrieve_done", k=k, filters=sorted(spec) or None, hits=len(hits),
                 policies=policies.names)
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
        policies = PolicySet.from_names(state.get("custom_policy"))
        gctx = GenerationContext(
            advisor=self.advisor, message=state["message"], hits=state.get("hits") or [],
            strategy=state.get("strategy"), expertise=state.get("expertise_level"),
            history="\n".join(history[:-1]) or None,  # [:-1] = exchanges before this turn
            llm=llm,
        )
        response = policies.run_generate(gctx, lambda c: c.execute())
        return {
            "response": response,
            "last_recommended_ids": [g.id_product for g in response.games],
            "history": [f"bot: {response.message}"],
        }

    # ---- API ---------------------------------------------------------------------

    def reply(self, message: str, choices: list[str] | None = None, k: int = 5,
              session_id: str = "default",
              custom_policy: list[str] | None = None) -> ChatResponse:
        """One stateful turn. Same return contract as ChatAdvisor.reply (Phase 4)."""
        out = self._graph.invoke(
            {"message": message, "choices": choices or [], "k": k,
             "custom_policy": custom_policy or []},
            config={"configurable": {"thread_id": session_id}},
        )
        return out["response"]

    def state(self, session_id: str) -> dict:
        """The checkpointed state of a session (debugging/tests)."""
        snapshot = self._graph.get_state({"configurable": {"thread_id": session_id}})
        return snapshot.values
