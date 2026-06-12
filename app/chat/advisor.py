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


from langchain_ollama import ChatOllama

from app.chat.models.reply import ChatReply
from app.chat.models.response import ChatResponse
from app.config import settings
from app.core.logging import get_logger
from app.core.tracing.callbacks import get_trace_callbacks
from app.models.game_hit import GameHit
from app.rag.filters.search_filters import SearchFilters
from app.rag.retriever import GameRetriever

log = get_logger(__name__)

# Honest fallback when nothing matches — the absolute rule says to say so, not to invent.
_NO_MATCH = (
    "Al momento non ho in catalogo un gioco che corrisponde bene a quello che cerchi. "
    "Prova a dirmi qualcosa in più: quante persone giocano, quanto tempo avete, o un gioco che "
    "ti è piaciuto."
)

# Default persona (Phase 4, no per-user analysis available).
_DEFAULT_PERSONA = (
    "Sei un commesso esperto e appassionato di giochi da tavolo. Aiuti il cliente a\n"
    "scegliere il gioco giusto in modo caldo, semplice e convincente — non sei un motore di ricerca."
)

# Fixed part of the Phase 5 prompt (docs/note.md): how to talk at each expertise level.
_EXPERTISE_RULES = """Sei un commesso esperto di giochi da tavolo, molto empatico. Aiuti il cliente a scegliere il
gioco giusto in modo caldo, semplice e convincente — non sei un motore di ricerca.
L'utente ha livello di esperienza: {expertise_level}.
Regole di comunicazione:
- Se beginner: usa linguaggio semplice, evita termini tecnici. Spiega sempre cosa significa una
  meccanica con un esempio ("cooperativo significa che tutti giocano contro il gioco, non tra di voi").
- Se intermediate: puoi usare qualche termine ma spiegalo la prima volta.
- Se advanced: usa terminologia precisa (worker placement, engine building, area control, ecc.).
Non dare per scontato che conosca le cose. Obiettivo: educare divertendo, mai far sentire stupido."""

# Dynamic part (docs/note.md): the behavior of the strategy the router picked for this turn.
_STRATEGY_RULES = {
    "GUIDED": (
        "Strategia per questo turno — GUIDED: il cliente è indeciso. Proponi al MASSIMO 2 "
        "giochi (mai più di 2 recommendations), con esempi concreti. OBBLIGATORIO: il `pitch` "
        "dell'ultimo gioco deve TERMINARE con una domanda semplice rivolta al cliente per "
        "capire meglio cosa cerca — l'ultima frase di quel `pitch` finisce con \"?\" "
        "(es. \"Preferite più una sfida a due o un gioco di squadra?\"). Le "
        "`quick_replies` NON sostituiscono questa domanda: va scritta dentro il `pitch`."
    ),
    "EXPLANATORY": (
        "Strategia per questo turno — EXPLANATORY: il cliente è curioso. Scegli i 2-3 giochi "
        "più adatti (NON tutta la lista) e spiega le loro meccaniche con linguaggio semplice "
        "e analogie (\"è come...\"), approfondendo dove mostra interesse."
    ),
    "DISCOVERY": (
        "Strategia per questo turno — DISCOVERY: stile libero e conversazionale. Parti da quello "
        "che il cliente racconta e proponi in modo creativo i giochi più affini."
    ),
    "QUICK_MATCH": (
        "Strategia per questo turno — QUICK MATCH: il cliente è pronto (o la conversazione va "
        "chiusa). Proponi SUBITO 3-4 giochi concreti dalla lista (ALMENO 3 recommendations), "
        "ognuno con una frase di vendita incisiva."
    ),
}


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
                expertise_level: str | None = None, history: str | None = None) -> str:
        """Fixed + dynamic prompt structure (docs/note.md).

        Without the Phase 5 keywords this is exactly the Phase 4 prompt. With them, the persona
        block carries the expertise communication rules, the strategy block carries the selling
        strategy of this turn, and the conversation so far gives the model context — the rigid
        anti-hallucination rules at the bottom are IDENTICAL on both paths.
        """
        catalog = "\n".join(self._game_line(i, h) for i, h in enumerate(hits))
        persona = (_EXPERTISE_RULES.format(expertise_level=expertise_level)
                   if expertise_level else _DEFAULT_PERSONA)
        conversation = f"\nCONVERSAZIONE FINORA:\n{history}\n" if history else ""
        strategy_block = f"\n{_STRATEGY_RULES[strategy]}\n" if strategy else ""
        return f"""{persona}
{conversation}
RICHIESTA DEL CLIENTE:
{message}

GIOCHI DISPONIBILI (gli UNICI che puoi proporre):
{catalog}

Regole rigide:
- Proponi SOLO giochi presenti nella lista qui sopra. NON inventare titoli e non usare la tua
  conoscenza di altri giochi: esistono solo quelli in lista.
- I consigli vivono SOLO in `recommendations`: un oggetto per OGNI gioco che proponi, con
  l'`id` ESATTO copiato dalla lista (il numero dopo "id=") e un `pitch` di 1-2 frasi che spiega
  PERCHÉ piacerà (tema, esperienza di gioco). Vendi l'esperienza, non elencare dati. Nel `pitch`
  nomina il gioco per NOME — mai l'`id`: è un codice interno, il cliente non deve vederlo.
- `intro`: UNA breve frase di apertura amichevole, senza nomi di giochi e senza `id`. L'intro da
  sola NON è una risposta: i giochi che prometti devono stare in `recommendations`.
- Quanti giochi proporre: segui la strategia di questo turno se indica un numero; altrimenti
  scegli i 2-3 più adatti alla richiesta.
- Se nessun gioco è davvero adatto, dillo onestamente nell'`intro` e proponi l'alternativa più
  vicina come unica recommendation.
- Scrivi in italiano, tono amichevole, breve.
- Compila SEMPRE 2-3 `quick_replies`: brevi affinamenti per il passo successivo. Quando il
  filtro è numerico usa ESATTAMENTE questi formati: "per N giocatori", "max N minuti",
  "dai N anni", "senza espansioni" (es. "per 2 giocatori", "max 60 minuti"); altrimenti testo
  libero breve (es. "Sorprendimi").

FORMATO DELLA RISPOSTA (JSON, TUTTI i campi obbligatori):
{{"intro": "<una frase di apertura>",
 "recommendations": [{{"id": <numero preso dalla lista>, "pitch": "<perché questo gioco piacerà>"}}, ...],
 "quick_replies": ["<affinamento breve>", ...]}}
`recommendations` NON può MAI essere vuota: ogni gioco che consigli deve comparirci con il suo
`id` e il suo `pitch`. Una risposta senza `recommendations` è una risposta sbagliata.
{strategy_block}"""

    # ---- API ------------------------------------------------------------------

    def reply(self, message: str, choices: list[str] | None = None,
              filters: SearchFilters | None = None, k: int = 5) -> ChatResponse:
        """Phase 4, stateless: quick-reply clicks are folded into the retrieval query.

        (The Phase 5 graph parses them into SearchFilters instead and calls `pitch` directly.)
        """
        query = f"{message}\n{' '.join(choices)}" if choices else message
        hits = self.retriever.search(query, k=k, filters=filters)
        return self.pitch(message, hits)

    def pitch(self, message: str, hits: list[GameHit], *, strategy: str | None = None,
              expertise_level: str | None = None, history: str | None = None,
              llm=None) -> ChatResponse:
        """Generate the grounded pitch over `hits` (the generation step alone).

        `llm` overrides the default model for this call — the model-tiering hook: the graph's
        generate node passes the strong model here when the analyze step escalated.
        """
        if not hits:
            return ChatResponse(message=_NO_MATCH, games=[], quick_replies=[])

        prompt = self._prompt(message, hits, strategy=strategy,
                              expertise_level=expertise_level, history=history)
        try:
            reply: ChatReply = (llm or self._llm).invoke(prompt)
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
