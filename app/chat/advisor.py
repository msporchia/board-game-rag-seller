"""ChatAdvisor — the generation half of RAG (Phase 4 core, reused by the Phase 5 graph).

Pipeline for one turn: retrieve real games from the catalog (hybrid search) → hand them to the
LLM as the ONLY allowed context → the LLM returns an intro plus per-game {id, pitch} pairs as
structured output → we validate the ids against the retrieved set and ASSEMBLE the customer
message in code (intro + surviving pitches). Binding each pitch to its id makes prose↔cards
incoherence structurally impossible: the text can only describe games that are in the cards.

Two invariants, both enforced in code (we do not trust the model):
  1. Anti-hallucination: a featured game must be in the retrieved set. The LLM references games
     by `id`; any id it returns that was not retrieved is dropped — together with its pitch. It
     can never surface a title that is not in the catalog (the absolute rule from docs/note.md).
  2. Robust transport: structured output (idee.md §A) constrains the JSON shape; if the local 8B
     still fails to produce it — or none of its picked ids survive validation — we fall back to
     a deterministic reply over the top hits rather than 500-ing.

Two entry points so the logic lives in ONE place:
  - `reply()`  — Phase 4, stateless: retrieve then pitch, one shot.
  - `pitch()`  — the generation step alone, over hits the caller already has. The Phase 5 graph
    calls this with `strategy` / `expertise_level` / `history` (which shape the prompt — the
    fixed+dynamic structure from docs/note.md) and optionally a different `llm` (model tiering:
    the escalation path passes the strong model). Grounding validation, message assembly and the
    deterministic fallback are identical on both paths.

Note: the prompt is intentionally in Italian — the bot speaks Italian to customers (system
behavior), like the enrichment prompts.
"""


from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.chat import prompts
from app.chat.models.customer_context import CustomerContext
from app.chat.models.reply import ChatReply
from app.chat.models.response import ChatResponse
from app.chat.policies.generation_context import GenerationContext
from app.chat.policies.policy_set import PolicySet
from app.chat.policies.retrieval_context import RetrievalContext
from app.config import settings
from app.core.logging import get_logger
from app.core.tracing.callbacks import get_trace_callbacks
from app.models.game_hit import GameHit
from app.rag.filters.search_filters import SearchFilters
from app.rag.retriever import GameRetriever

log = get_logger(__name__)

# Prompt text lives in app/chat/prompts.py (one findable place). `_NO_MATCH` stays re-exported
# here because it's the advisor's honest empty-reply, asserted by tests.
_NO_MATCH = prompts.NO_MATCH


class ChatAdvisor:
    def __init__(self, retriever: GameRetriever | None = None, llm=None,
                 model: str | None = None, base_url: str | None = None,
                 temperature: float = 0.4):
        self.retriever = retriever or GameRetriever()
        self.model = model or settings.llm_model
        # `llm` is any object with `.invoke(prompt) -> ChatReply`. Default: ChatOllama constrained
        # to the ChatReply schema. Tests inject a fake to stay offline and deterministic.
        self._llm = llm or ChatOllama(
            model=self.model, base_url=base_url or settings.ollama_url, temperature=temperature,
            callbacks=get_trace_callbacks("chat.generate"), tags=["chat"],
        ).with_structured_output(ChatReply)

    # ---- context assembly -----------------------------------------------------

    @staticmethod
    def _game_line(i: int, h: GameHit) -> str:
        """One retrieved game, labeled for the LLM. `i` is the stable id we ask it to cite."""
        parts = [f"[id={h.id_product}] {h.name}"]
        if h.categoria:
            parts.append(f"categoria: {h.categoria}")
        if h.tags:
            parts.append(f"temi/meccaniche: {', '.join(h.tags)}")
        if h.players:
            lo, hi = min(h.players), max(h.players)
            parts.append(f"giocatori: {h.players_display or (lo if lo == hi else f'{lo}-{hi}')}")
        if h.duration_min:
            parts.append(f"durata: {h.duration_min} min")
        if h.complexity:
            parts.append(f"complessità: {h.complexity}")
        return " | ".join(parts)

    def _prompt(self, message: str, hits: list[GameHit], *, strategy: str | None = None,
                expertise_level: str | None = None, history: str | None = None,
                extra_blocks: list[str] | None = None,
                customer_block: str | None = None) -> list:
        """Fixed + dynamic prompt structure (docs/note.md), split into roles (SEL-122).

        Instruction/data separation: every INSTRUCTION and every piece of TRUSTED data (persona,
        the retrieved catalog, active-policy blocks, customer context, grounding rules, response
        format, this turn's strategy) lives in the SystemMessage; the untrusted customer turn is
        the sole HumanMessage. The role boundary is the delimiter — the customer's text is never
        interpolated among the rules, so a turn that says "ignore the rules" is presented as data in
        its own role rather than mixed into the instructions. This is a hardening step, not a
        guarantee the model obeys (SEL-122 tracks the wider analysis). The rule text itself is
        unchanged; only the routing into roles is new.

        Without the Phase 5 keywords the system block is exactly the Phase 4 prompt. With them, the
        persona block carries the expertise communication rules, the strategy block carries the
        selling strategy of this turn, and the conversation so far gives the model context — the
        rigid anti-hallucination rules are IDENTICAL on both paths.

        `extra_blocks` are instruction blocks contributed by the active policies (PolicySet,
        docs/idee.md §O): they reshape the prose, never the grounding rules below.
        """
        catalog = "\n".join(self._game_line(i, h) for i, h in enumerate(hits))
        persona = (prompts.EXPERTISE_RULES.format(expertise_level=expertise_level)
                   if expertise_level else prompts.DEFAULT_PERSONA)
        conversation = f"\nCONVERSAZIONE FINORA:\n{history}\n" if history else ""
        strategy_block = f"\n{prompts.STRATEGY_RULES[strategy]}\n" if strategy else ""
        policy_text = "\n".join(b for b in (extra_blocks or []) if b)
        sales_block = f"\nPOLICY ATTIVE:\n{policy_text}\n" if policy_text else ""
        client_block = f"\nCONTESTO CLIENTE:\n{customer_block}\n" if customer_block else ""
        system = f"""{persona}
{conversation}
GIOCHI DISPONIBILI (gli UNICI che puoi proporre):
{catalog}
{client_block}{sales_block}

{prompts.GROUNDING_RULES}

{prompts.RESPONSE_FORMAT}
{strategy_block}"""
        return [SystemMessage(content=system), HumanMessage(content=message)]

    # ---- API ------------------------------------------------------------------

    def reply(self, message: str, choices: list[str] | None = None,
              filters: SearchFilters | None = None, k: int = 5,
              custom_policy: list[str] | None = None,
              customer_context: CustomerContext | None = None) -> ChatResponse:
        """Phase 4, stateless: quick-reply clicks are folded into the retrieval query.

        (The Phase 5 graph parses them into SearchFilters instead and calls `pitch` directly.)

        Active policies (docs/idee.md §O) wrap BOTH stages here too: retrieval through the
        policy chain (a policy may reshape the query/filters/hits) and generation through it
        (prompt blocks, llm), plus the expertise/strategy shortcuts. `customer_context` (Phase 6)
        rides through generation, where the enforced-vs-generated split is applied.
        """
        policies = PolicySet.from_names(custom_policy)
        query = f"{message}\n{' '.join(choices)}" if choices else message
        rctx = RetrievalContext(query=query, k=k, retriever=self.retriever, filters=filters,
                                exclude_ids=customer_context.received_products
                                if customer_context else None)
        hits = policies.run_retrieve(rctx)
        strategy = policies.force_strategy(None)
        gctx = GenerationContext(
            advisor=self, message=message, hits=hits,
            strategy=strategy.value if strategy else None,
            expertise=policies.force_expertise(None),
            customer_context=customer_context,
        )
        return policies.run_generate(gctx)

    def pitch(self, message: str, hits: list[GameHit], *, strategy: str | None = None,
              expertise_level: str | None = None, history: str | None = None,
              llm=None, extra_blocks: list[str] | None = None,
              customer_context: CustomerContext | None = None) -> ChatResponse:
        """Generate the grounded pitch over `hits` (the generation step alone).

        `llm` overrides the default model for this call — the model-tiering hook: the graph's
        generate node passes the strong model here when the analyze step escalated.
        `extra_blocks` are policy-contributed instruction blocks (PolicySet, docs/idee.md §O).
        `customer_context` (Phase 6) is the GENERATED half of the split: cart/sent games are framed
        in the prompt as already-chosen/on-the-way. The ENFORCED half (dropping owned games) now
        happens earlier, at retrieval (`exclude_ids` → Qdrant `must_not`), so by here the hits are
        already owned-free and an owned game simply isn't in the retrieved set to ground against.
        """
        if not hits:  # nothing left to pitch (empty retrieval, or all candidates already owned)
            return ChatResponse(message=_NO_MATCH, games=[], quick_replies=[])

        customer_block = customer_context.framing_block(hits) if customer_context else None
        messages = self._prompt(message, hits, strategy=strategy,
                                expertise_level=expertise_level, history=history,
                                extra_blocks=extra_blocks, customer_block=customer_block)
        try:
            reply: ChatReply = (llm or self._llm).invoke(messages)
        except Exception:  # noqa: BLE001  LLM/transport failure → deterministic fallback, never 500
            log.warning("pitch_llm_failed", fallback="deterministic_pitch")
            return self._fallback(hits)

        # Anti-hallucination: keep only recommendations whose id was actually retrieved,
        # preserving the LLM order, each id at most once (small models sometimes pitch the same
        # game twice). An invented id loses its pitch too — the assembled message can therefore
        # only ever describe games that are in the cards (coherence by construction).
        by_id = {h.id_product: h for h in hits}
        kept, seen = [], set()
        for r in reply.recommendations or []:
            if r.id in by_id and r.id not in seen:
                kept.append(r)
                seen.add(r.id)
        if not kept:  # nothing valid → no grounded pitch to show, degrade to the deterministic reply
            return self._fallback(hits)
        games = [by_id[r.id] for r in kept]
        parts = [(reply.intro or "").strip()] + [(r.pitch or "").strip() for r in kept]
        message = " ".join(p for p in parts if p)
        return ChatResponse(
            message=message or self._plain_pitch(games),
            games=games,
            quick_replies=(reply.quick_replies or [])[:3],
        )

    # ---- deterministic fallback (no LLM) --------------------------------------

    def _fallback(self, hits: list[GameHit]) -> ChatResponse:
        top = hits[:3]
        return ChatResponse(message=self._plain_pitch(top), games=top, quick_replies=[])

    @staticmethod
    def _plain_pitch(games: list[GameHit]) -> str:
        names = ", ".join(g.name for g in games)
        return f"Dai un'occhiata a questi: {names}."
