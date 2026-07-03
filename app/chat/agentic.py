"""AgenticChat — the experimental tool-calling engine (Phase 6 groundwork, docs/idee.md §Q).

The agentic tier the TieredChat seam was built for: a strong model that decides WHEN and WITH
WHAT WORDS to search, driving the `search_catalog` tool itself instead of the code orchestrating
it (the pipeline) or piloting it one constrained step at a time (the piloted engine).

Same `reply(...)` contract as the other engines, so it drops into TieredChat's primary slot
behind `engine=agent`. The three invariants stay in CODE at the boundary, exactly as §Q
prescribes: the model's tool calls only RETRIEVE; the customer-facing answer is still produced by
the grounded `ChatAdvisor.pitch` over the UNION of everything the tool returned (so a featured
game must have been retrieved), with the honest no-match and deterministic fallback unchanged.
Active policies wrap that generation step (prompt blocks, forced expertise) like everywhere else.

STUB scope (deliberately minimal — this is groundwork, not the production agent): an in-process
session memory (the conversation so far is fed back into the model's messages so a follow-up turn
has context — NOT a checkpointed graph state), no click→filter merge, no circuit breaker (§Q). The
local 8B cannot drive tools reliably, which is the whole reason this sits behind TieredChat: when
the model emits no usable tool call the turn degrades to an honest no-match, and a transport
failure degrades to the pipeline fallback. Tests inject a fake tool-calling LLM to exercise the
loop offline; in production point `llm_model_strong` at an agentic-native model.

`state()` is the agent's HONEST end-of-turn report (the searches it ran, the hits it found), not
a piloted graph state — the agent is black-box, so it is measured end-to-end (did the interaction
converge? did it use the structured filters? at what cost?), never by spying on intermediate state.
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from app.chat import prompts
from app.chat.advisor import ChatAdvisor
from app.chat.models.customer_context import CustomerContext
from app.chat.models.response import ChatResponse
from app.chat.policies.generation_context import GenerationContext
from app.chat.policies.policy_set import PolicySet
from app.chat.tools.search_catalog import SearchCatalogTool
from app.config import settings
from app.core.logging import get_logger
from app.core.tracing.callbacks import get_trace_callbacks

log = get_logger(__name__)

# Tool-loop budget (§Q): at most this many LLM rounds; each round may request searches, then the
# turn must answer over what was found. Bounds the most expensive (and least reliable) path.
MAX_ROUNDS = 3

# Rolling window of conversation entries kept per session (≈ 6 exchanges), like ChatState.
HISTORY_MAX = 12


class AgenticChat:
    """The compiled agentic engine. Same contract and lifecycle as ChatGraph/PilotedChat."""

    def __init__(self, advisor: ChatAdvisor | None = None, llm=None, max_rounds: int = MAX_ROUNDS):
        self.advisor = advisor or ChatAdvisor()
        self.max_rounds = max_rounds
        self._model = settings.llm_model_strong or settings.llm_model
        # Any chat model with `.bind_tools(...)` and `.invoke(messages) -> AIMessage`. Default:
        # the strong model (tool-calling is the strong tier's job). Tests inject a fake.
        self._llm = llm or ChatOllama(
            model=self._model, base_url=settings.ollama_url, temperature=0.2,
            callbacks=get_trace_callbacks("chat.agent"),
        )
        # The last turn's searches, the agent's equivalent of the piloted engine's
        # `turn_searches`: one record per tool call — {query, filters, n_hits, hit_ids} — so a
        # debugger/eval can see WHAT the model searched for and, crucially, whether it used the
        # structured constraint fields (players/duration) or stuffed everything into free text
        # (`filters` empty → a crude, all-text query).
        self.last_turn_searches: list[dict] = []
        # In-process per-session memory: {session_id: {history: [(role, text)], hits, searches}}.
        # The conversation so far is fed back into the model's messages; `state()` reports the
        # last turn's hits/searches. Process-local (not checkpointed) — stub-grade, enough for the
        # experimental tier and the end-to-end eval.
        self._sessions: dict[str, dict] = {}

    def reply(self, message: str, choices: list[str] | None = None, k: int = 5,
              session_id: str = "default",
              custom_policy: list[str] | None = None,
              customer_context: CustomerContext | None = None) -> ChatResponse:
        policies = PolicySet.from_names(custom_policy)
        session = self._sessions.setdefault(session_id,
                                            {"history": [], "hits": [], "searches": []})
        tool = SearchCatalogTool(retriever=self.advisor.retriever, k=k,
                                 exclude_ids=customer_context.received_products
                                 if customer_context else None)
        llm = self._llm.bind_tools([tool.as_tool()])

        # The conversation so far feeds the model's context (the agent is not piloted: it reads
        # the whole exchange and decides its own queries — a follow-up turn knows the prior ones).
        messages = [SystemMessage(content=prompts.AGENT_SYSTEM)]
        for role, text in session["history"]:
            messages.append(HumanMessage(content=text) if role == "user"
                            else AIMessage(content=text))
        messages.append(HumanMessage(content=message))
        hits_by_id: dict[int, object] = {}  # union across all tool calls, first occurrence wins
        searches: list[dict] = []
        rounds = 0
        while rounds < self.max_rounds:
            rounds += 1
            ai = llm.invoke(messages)
            messages.append(ai)
            tool_calls = getattr(ai, "tool_calls", None) or []
            if not tool_calls:
                break
            for call in tool_calls:
                try:
                    found = tool.run(**(call.get("args") or {}))
                except Exception as exc:  # noqa: BLE001 — a bad tool call must not kill the turn
                    log.warning("agent_tool_call_failed", args=call.get("args"), error=str(exc))
                    messages.append(ToolMessage(
                        content="Ricerca fallita: riprova con argomenti più semplici.",
                        tool_call_id=call.get("id", "")))
                    continue
                intent = tool.calls[-1]  # the SearchIntent the model just produced
                record = {"query": intent.query, "filters": intent.to_filters_spec(),
                          "n_hits": len(found), "hit_ids": [h.id_product for h in found]}
                searches.append(record)
                log.info("agent_search_done", query=record["query"],
                         filters=record["filters"] or None, n_hits=record["n_hits"],
                         hit_ids=record["hit_ids"])
                for hit in found:
                    hits_by_id.setdefault(hit.id_product, hit)
                names = ", ".join(h.name for h in found) or "nessuno"
                messages.append(ToolMessage(content=f"{len(found)} giochi: {names}",
                                            tool_call_id=call.get("id", "")))

        if not searches:
            # SEL-147: on later turns the local model sometimes stops emitting tool calls
            # altogether, which used to collapse the turn into a FALSE honest no-match (the
            # catalog did stock what was asked — nobody searched). Enforced floor, same spirit
            # as the grounding split: the model drives the search when it drives; when it
            # doesn't, the CODE runs one plain search with the customer's own words before the
            # turn is allowed to give up. The record is flagged `forced` so eval/showcase can
            # tell model-driven searches from the safety net.
            try:
                found = tool.run(query=message)
            except Exception:  # noqa: BLE001 — the floor must never kill the turn
                log.warning("agent_forced_search_failed", exc_info=True)
                found = []
            else:
                intent = tool.calls[-1]
                searches.append({"query": intent.query, "filters": intent.to_filters_spec(),
                                 "n_hits": len(found),
                                 "hit_ids": [h.id_product for h in found], "forced": True})
                log.info("agent_search_forced", n_hits=len(found))
            for hit in found:
                hits_by_id.setdefault(hit.id_product, hit)

        hits = list(hits_by_id.values())
        self.last_turn_searches = searches
        log.info("agent_turn_done", rounds=rounds, searches=len(searches),
                 hits=len(hits), policies=policies.names)
        history_text = "\n".join(
            f"{'utente' if role == 'user' else 'bot'}: {text}"
            for role, text in session["history"]) or None
        gctx = GenerationContext(advisor=self.advisor, message=message, hits=hits,
                                 expertise=policies.force_expertise(None),
                                 history=history_text, customer_context=customer_context)
        response = policies.run_generate(gctx)

        session["history"] = (session["history"]
                              + [("user", message), ("bot", response.message)])[-HISTORY_MAX:]
        session["hits"] = hits
        session["searches"] = searches
        return response

    def state(self, session_id: str) -> dict:
        """The agent's honest end-of-turn report (debugging/eval), NOT a checkpointed graph state.

        The agent is black-box, not piloted: it exposes only what it actually did this turn — the
        last hits and the searches the model itself ran. `strategy` is None (no router) and
        `filters_spec` is None (no cross-turn filter accumulation), so the pipeline/piloted-shaped
        oracles are out of scope for it by design; only the end-to-end outcomes (convergence,
        grounding, tool-use, cost) are measured.
        """
        session = self._sessions.get(session_id, {})
        return {"strategy": None, "filters_spec": None, "hits": session.get("hits", []),
                "turn_searches": session.get("searches", [])}
