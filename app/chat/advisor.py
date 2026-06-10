"""ChatAdvisor — the generation half of RAG (Phase 4, stateless).

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

Stateless on purpose: no session memory, no strategy routing, no model tiering — those are
Phase 5 (a stateful LangGraph wrapping this same retrieve→pitch core). See docs/chat.md.

Note: the prompt is intentionally in Italian — the bot speaks Italian to customers (system
behavior), like the enrichment prompts.
"""

from langchain_ollama import ChatOllama

from app.chat.models import ChatReply, ChatResponse
from app.config import settings
from app.core.tracing import get_trace_callbacks
from app.models import GameHit
from app.rag.filters import SearchFilters
from app.rag.retriever import GameRetriever

# Honest fallback when nothing matches — the absolute rule says to say so, not to invent.
_NO_MATCH = (
    "Al momento non ho in catalogo un gioco che corrisponde bene a quello che cerchi. "
    "Prova a dirmi qualcosa in più: quante persone giocano, quanto tempo avete, o un gioco che "
    "ti è piaciuto."
)


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
            callbacks=get_trace_callbacks("chat"), tags=["chat"],
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

    def _prompt(self, message: str, hits: list[GameHit]) -> str:
        catalog = "\n".join(self._game_line(i, h) for i, h in enumerate(hits))
        return f"""Sei un commesso esperto e appassionato di giochi da tavolo. Aiuti il cliente a
scegliere il gioco giusto in modo caldo, semplice e convincente — non sei un motore di ricerca.

RICHIESTA DEL CLIENTE:
{message}

GIOCHI DISPONIBILI (gli UNICI che puoi proporre):
{catalog}

Regole rigide:
- Proponi SOLO giochi presenti nella lista qui sopra. NON inventare titoli e non usare la tua
  conoscenza di altri giochi: esistono solo quelli in lista.
- `intro`: UNA breve frase di apertura amichevole, senza nomi di giochi e senza `id`.
- `recommendations`: scegli i 2-3 giochi più adatti alla richiesta. Per ciascuno metti l'`id`
  ESATTO preso dalla lista e un `pitch` di 1-2 frasi che spiega PERCHÉ piacerà (tema, esperienza
  di gioco). Vendi l'esperienza, non elencare dati. Nel `pitch` nomina il gioco per NOME — mai
  l'`id`: è un codice interno, il cliente non deve vederlo.
- Se nessun gioco è davvero adatto, dillo onestamente nell'`intro` e proponi l'alternativa più
  vicina come unica recommendation.
- Scrivi in italiano, tono amichevole, breve.
- Compila SEMPRE 2-3 `quick_replies`: brevi affinamenti per il passo successivo
  (es. "Solo cooperativi", "Max 1 ora", "Sorprendimi").

Restituisci: `intro`, le `recommendations` (id + pitch per ogni gioco scelto) e le `quick_replies`."""

    # ---- API ------------------------------------------------------------------

    def reply(self, message: str, choices: list[str] | None = None,
              filters: SearchFilters | None = None, k: int = 5) -> ChatResponse:
        # Phase 4: quick-reply clicks are folded into the retrieval query (Phase 5 → filters).
        query = f"{message}\n{' '.join(choices)}" if choices else message
        hits = self.retriever.search(query, k=k, filters=filters)
        if not hits:
            return ChatResponse(message=_NO_MATCH, games=[], quick_replies=[])

        try:
            reply: ChatReply = self._llm.invoke(self._prompt(message, hits))
        except Exception:  # noqa: BLE001  LLM/transport failure → deterministic fallback, never 500
            return self._fallback(hits)

        # Anti-hallucination: keep only recommendations whose id was actually retrieved,
        # preserving the LLM order. An invented id loses its pitch too — the assembled message
        # can therefore only ever describe games that are in the cards (coherence by construction).
        by_id = {h.id_product: h for h in hits}
        kept = [r for r in (reply.recommendations or []) if r.id in by_id]
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
