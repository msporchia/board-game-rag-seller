"""PilotedChat — arm B: the code-piloted agent loop (docs/idee.md §Q).

Same loop SHAPE as the autonomous agent, but the graph orchestrates and the weak model does one
constrained job per step:

    START → intent → search ──(zero hits, budget left)──> retry ──(new query)──┐
                       ↑  └────────(hits, or budget spent)──> generate → END   │
                       └────────────────────────────────────────────────────────┘

- intent    one structured LLM call per turn: given the conversation, the model expresses what
            it would recommend — a reformulated search query in catalog language plus the
            constraints the customer actually declared (SearchIntent). The retrieval query is
            the MODEL's reformulation, never the user's verbatim text (generate-then-retrieve:
            it translates customer paraphrase into the catalog language the embedder can match).
- search    CODE does the fetch: quick-reply clicks stay hard filters exactly as in the
            pipeline (parse_choices + latest-wins merge, unchanged); the model's proposed
            constraints apply only where no click covers the dimension — the model proposes,
            the code disposes. Searching EVERY turn on fresh intent subsumes the pipeline's
            re-retrieval skip-condition (the GUIDED staleness failure class).
- retry     only on ZERO hits, at most once (budget: 2 searches per turn): the model is TOLD
            the search returned nothing and chooses, structured — a new query, or the honest
            no-match. Its own proposed constraints are dropped on retry (the likeliest culprit);
            click filters stay hard — the retry cannot bypass the customer's explicit choices.
- generate  ChatAdvisor.pitch, unchanged: grounding against the hits of THIS turn's searches,
            the ChatReply contract, the honest no-match and the deterministic fallback — the
            three invariants live in the same code as the pipeline's.

ChatState stays the lingua franca (same history/filters_spec shape, same checkpointer), which
is what keeps any single turn servable by either engine — TieredChat can degrade a piloted
turn to the pipeline mid-session. Unlike the pipeline there is no strategy router: every turn
honors the request's k.
"""

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from app.chat.advisor import ChatAdvisor
from app.chat.checkpointer import sqlite_checkpointer
from app.chat.choices import parse_choices
from app.chat.models.customer_context import CustomerContext
from app.chat.models.intent import SearchIntent
from app.chat.models.response import ChatResponse
from app.chat.models.retry import RetryDecision
from app.chat.policies.generation_context import GenerationContext
from app.chat.policies.policy_set import PolicySet
from app.chat.policies.retrieval_context import RetrievalContext
from app.chat.state import ChatState, merge_filters
from app.config import settings
from app.core.logging import get_logger
from app.core.tracing.callbacks import get_trace_callbacks

log = get_logger(__name__)

# Hard cap on retrieval calls per turn: the first search plus ONE explicit retry.
MAX_SEARCHES_PER_TURN = 2


class PilotedChat:
    """The compiled arm-B graph. Same contract and lifecycle as ChatGraph."""

    def __init__(self, advisor: ChatAdvisor | None = None, intent_llm=None, retry_llm=None,
                 checkpointer=None):
        self.advisor = advisor or ChatAdvisor()
        # Both piloted steps are classification-shaped: weak model, temperature 0. Tests inject
        # fakes; the schemas differ, so they are two constrained views over the same model.
        self._intent_llm = intent_llm or ChatOllama(
            model=settings.llm_model, base_url=settings.ollama_url, temperature=0.0,
            callbacks=get_trace_callbacks("chat.intent"),
        ).with_structured_output(SearchIntent)
        self._retry_llm = retry_llm or ChatOllama(
            model=settings.llm_model, base_url=settings.ollama_url, temperature=0.0,
            callbacks=get_trace_callbacks("chat.retry"),
        ).with_structured_output(RetryDecision)
        self._graph = self._build(checkpointer or sqlite_checkpointer())

    # ---- graph wiring ----------------------------------------------------------

    def _build(self, checkpointer):
        builder = StateGraph(ChatState)
        builder.add_node("intent", self._intent)
        builder.add_node("search", self._search)
        builder.add_node("retry", self._retry)
        builder.add_node("generate", self._generate)

        builder.add_edge(START, "intent")
        builder.add_edge("intent", "search")
        builder.add_conditional_edges("search", self._after_search,
                                      {"retry": "retry", "generate": "generate"})
        builder.add_conditional_edges("retry", self._after_retry,
                                      {"search": "search", "generate": "generate"})
        builder.add_edge("generate", END)
        return builder.compile(checkpointer=checkpointer)

    # ---- prompts (Italian, like every catalog-facing prompt) ---------------------

    @staticmethod
    def _intent_prompt(history: list[str], message: str, session_spec: dict) -> str:
        conversation = "\n".join(history) if history else "(inizio conversazione)"
        active = (", ".join(f"{name}={params}" for name, params in sorted(session_spec.items()))
                  or "(nessuno)")
        return f"""Lavori nel retrobottega di un negozio di giochi da tavolo: leggi la conversazione e
prepari la RICERCA A CATALOGO per il commesso. Non parli con il cliente.

CONVERSAZIONE FINORA:
{conversation}

ULTIMO MESSAGGIO DEL CLIENTE:
{message}

FILTRI GIÀ ATTIVI (scelti dal cliente con i click, li applica già il sistema):
{active}

Pensa a quale gioco consiglieresti e descrivi QUEL gioco. Compila:
- query: la descrizione del gioco ideale nel linguaggio delle schede di catalogo (tema,
  meccaniche, tipo di esperienza, per chi è). NON copiare le parole del cliente: traducile
  nel gergo del catalogo. Esempio: il cliente dice "vorrei che si giocasse tutti insieme
  contro il gioco" → query "gioco cooperativo per famiglie, si vince e si perde insieme".
  Tieni nella query anche i bisogni emersi nei turni precedenti che restano validi.
- players / max_minutes / youngest_player_age: SOLO i vincoli che il cliente ha dichiarato
  (numero di giocatori, durata massima in minuti, età del giocatore più giovane). Lascia
  vuoto ciò che non ha detto: un vincolo inventato esclude giochi validi."""

    @staticmethod
    def _retry_prompt(message: str, query: str, effective_spec: dict) -> str:
        active = (", ".join(f"{name}={params}" for name, params in sorted(effective_spec.items()))
                  or "(nessuno)")
        return f"""La ricerca a catalogo NON ha prodotto NESSUN risultato.

RICHIESTA DEL CLIENTE:
{message}

QUERY PROVATA:
{query}

FILTRI APPLICATI:
{active}

Decidi onestamente:
- se la query può essere riformulata meglio (termini diversi, più generale), compila `query`
  con la nuova formulazione e metti no_match=false;
- se i vincoli del cliente rendono la richiesta impossibile da soddisfare, metti no_match=true:
  il commesso dirà onestamente che non abbiamo un gioco adatto.
I filtri scelti con i click dal cliente restano attivi: la nuova query non può aggirarli."""

    # ---- nodes -------------------------------------------------------------------

    def _intent(self, state: ChatState) -> dict:
        """One structured LLM call: the model's recommendation intent → query + constraints.

        Also resets the per-turn scratch channels (search budget, retry outcome, search log).
        On any intent failure the turn degrades to the user's text with no proposed
        constraints — worse retrieval, but the customer still gets a grounded reply; behind
        TieredChat a systemic failure is the wrapper's business, not a 500 here.
        """
        message = state["message"]
        session_spec = merge_filters(state.get("filters_spec"),
                                     parse_choices(state.get("choices"))[0])
        try:
            intent: SearchIntent = self._intent_llm.invoke(
                self._intent_prompt(state.get("history") or [], message, session_spec))
        except Exception:  # noqa: BLE001 — the intent failing must never kill the turn
            log.warning("intent_llm_failed", fallback="verbatim_query")
            intent = SearchIntent()
        query = intent.query.strip() or message
        proposed = intent.to_filters_spec()
        log.info("intent_done", query=query, proposed=sorted(proposed) or None)
        return {
            "intent_query": query,
            "proposed_spec": proposed,
            "searches_used": 0,
            "gave_up": False,
            "turn_searches": [],
            "history": [f"utente: {message}"],
        }

    def _search(self, state: ChatState) -> dict:
        """CODE fetches with the model's query: clicks are hard filters exactly as in the
        pipeline; model-proposed constraints fill only the dimensions no click covers. The fetch
        runs through the policy chain (RetrievalContext), same as the pipeline's retrieve node."""
        fragment, leftovers = parse_choices(state.get("choices"))
        effective = self._effective_spec(state)

        # Free-form clicks ("Sorprendimi") ride the query, same degradation as the pipeline.
        query = "\n".join([state["intent_query"], *leftovers])
        k = state.get("k") or 5
        policies = PolicySet.from_names(state.get("custom_policy"))
        rctx = RetrievalContext(query=query, k=k, retriever=self.advisor.retriever,
                                filters_spec=effective)
        hits = policies.run_retrieve(rctx, lambda c: c.execute())
        used = (state.get("searches_used") or 0) + 1
        log.info("piloted_search_done", search=used, k=k,
                 filters=sorted(effective) or None, hits=len(hits), policies=policies.names)
        return {
            "hits": hits,
            "filters_spec": fragment,
            "searches_used": used,
            "turn_searches": [*(state.get("turn_searches") or []),
                              {"query": rctx.query, "filters": effective, "n_hits": len(hits),
                               "hit_ids": [h.id_product for h in hits]}],
        }

    def _retry(self, state: ChatState) -> dict:
        """The informed zero-result decision: the model SAW the empty result and chooses a new
        query or the honest no-match. Its proposed constraints are dropped on retry (the
        likeliest culprit); click filters stay — code-managed, not negotiable."""
        try:
            decision: RetryDecision = self._retry_llm.invoke(
                self._retry_prompt(state["message"], state["intent_query"],
                                   self._effective_spec(state)))
        except Exception:  # noqa: BLE001 — a failed retry decision = give up honestly
            log.warning("retry_llm_failed", fallback="honest_no_match")
            decision = RetryDecision(no_match=True)
        query = decision.query.strip()
        if decision.no_match or not query:
            log.info("retry_done", outcome="no_match")
            return {"gave_up": True}
        log.info("retry_done", outcome="retry", query=query)
        return {"intent_query": query, "proposed_spec": {}, "gave_up": False}

    def _generate(self, state: ChatState) -> dict:
        """ChatAdvisor.pitch over THIS turn's hits — the same grounded path as the pipeline:
        valid ids are only what this turn's searches returned; empty hits → honest no-match."""
        history = state.get("history") or []
        policies = PolicySet.from_names(state.get("custom_policy"))
        gctx = GenerationContext(
            advisor=self.advisor, message=state["message"], hits=state.get("hits") or [],
            history="\n".join(history[:-1]) or None,  # [:-1] = exchanges before this turn
            expertise=policies.force_expertise(None),
            customer_context=state.get("customer_context"),
        )
        response = policies.run_generate(gctx, lambda c: c.execute())
        return {
            "response": response,
            "last_recommended_ids": [g.id_product for g in response.games],
            "history": [f"bot: {response.message}"],
        }

    # ---- edges -------------------------------------------------------------------

    @staticmethod
    def _after_search(state: ChatState) -> str:
        """Zero hits with budget left → ask the model; anything else goes to generate."""
        if not state.get("hits") and (state.get("searches_used") or 0) < MAX_SEARCHES_PER_TURN:
            return "retry"
        return "generate"

    @staticmethod
    def _after_retry(state: ChatState) -> str:
        return "generate" if state.get("gave_up") else "search"

    @staticmethod
    def _effective_spec(state: ChatState) -> dict:
        """Model-proposed constraints under the session's click filters (clicks win)."""
        fragment, _ = parse_choices(state.get("choices"))
        session = merge_filters(state.get("filters_spec"), fragment)
        return merge_filters(state.get("proposed_spec"), session)

    # ---- API ---------------------------------------------------------------------

    def reply(self, message: str, choices: list[str] | None = None, k: int = 5,
              session_id: str = "default",
              custom_policy: list[str] | None = None,
              customer_context: CustomerContext | None = None) -> ChatResponse:
        """One stateful turn. Same contract as ChatGraph.reply."""
        out = self._graph.invoke(
            {"message": message, "choices": choices or [], "k": k,
             "custom_policy": custom_policy or [], "customer_context": customer_context},
            config={"configurable": {"thread_id": session_id}},
        )
        return out["response"]

    def state(self, session_id: str) -> dict:
        """The checkpointed state of a session (debugging/tests)."""
        snapshot = self._graph.get_state({"configurable": {"thread_id": session_id}})
        return snapshot.values
