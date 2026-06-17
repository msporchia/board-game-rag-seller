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

STUB scope (deliberately minimal — this is groundwork, not the production agent): per-turn,
stateless (no session history yet), no click→filter merge, no circuit breaker (§Q). The local
8B cannot drive tools reliably, which is the whole reason this sits behind TieredChat: when the
model emits no usable tool call the turn degrades to an honest no-match, and a transport failure
degrades to the pipeline fallback. Tests inject a fake tool-calling LLM to exercise the loop
offline; in production point `llm_model_strong` at an agentic-native model.
"""

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from app.chat.advisor import ChatAdvisor
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

_SYSTEM = (
    "Sei il commesso di un negozio di giochi da tavolo. Per consigliare devi prima cercare a "
    "catalogo con lo strumento search_catalog: puoi proporre solo giochi che lo strumento "
    "restituisce. Cerca con parole del catalogo (tema, meccaniche, esperienza). Quando hai "
    "abbastanza giochi adatti, smetti di cercare."
)


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

    def reply(self, message: str, choices: list[str] | None = None, k: int = 5,
              session_id: str = "default",
              custom_policy: list[str] | None = None) -> ChatResponse:
        policies = PolicySet.from_names(custom_policy)
        tool = SearchCatalogTool(retriever=self.advisor.retriever, k=k)
        llm = self._llm.bind_tools([tool.as_tool()])

        messages = [SystemMessage(content=_SYSTEM), HumanMessage(content=message)]
        hits_by_id: dict[int, object] = {}  # union across all tool calls, first occurrence wins
        rounds = 0
        while rounds < self.max_rounds:
            rounds += 1
            ai = llm.invoke(messages)
            messages.append(ai)
            tool_calls = getattr(ai, "tool_calls", None) or []
            if not tool_calls:
                break
            for call in tool_calls:
                found = tool.run(**(call.get("args") or {}))
                for hit in found:
                    hits_by_id.setdefault(hit.id_product, hit)
                names = ", ".join(h.name for h in found) or "nessuno"
                messages.append(ToolMessage(content=f"{len(found)} giochi: {names}",
                                            tool_call_id=call.get("id", "")))

        hits = list(hits_by_id.values())
        log.info("agent_turn_done", rounds=rounds, searches=len(tool.calls),
                 hits=len(hits), policies=policies.names)
        gctx = GenerationContext(advisor=self.advisor, message=message, hits=hits,
                                 expertise=policies.force_expertise(None))
        return policies.run_generate(gctx, lambda c: c.execute())
