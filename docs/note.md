# Notes — raw brain-dump

Relevant ideas (kept informal on purpose — this is the scratchpad):

- A quality check should be done before inserting games; if they don't pass it, set a flag or
  something to mark them 'low quality' and treat them specially (e.g. extract them only once
  the other hypotheses are exhausted, with a stricter prompt).
- Evaluate enrichment for some specific games (e.g. of a category, or with no similar games,
  just released, etc.) by searching reviews and other info online.
- We need persistent memory of the games the user has visited (the last N, say) — like Claude
  Code knowing which tabs are open — to give the user contextual info and infer something useful
  from what they've already seen.
- We also need memory of past chats, probably compressed/summarized, but framed as "a while ago
  they said…" so it's handled the right way.

Example user profile:

```json
{
  "user_id": 12345,
  "preferred_players": [2, 3, 4],
  "hates": ["Monopoly", "pure luck", "economic games"],
  "loves": ["cooperative", "fantasy", "storytelling"],
  "past_games": ["Le Cronache di Avel", "Dixit"],
  "skill_level": "beginner",
  "last_recommendations": [...]
}
```

- Evaluate LangGraph or Qdrant itself for user memories (weigh the pros and cons).

The idea is to understand the user's level interactively from the terms they use, and manage the
target accordingly.

Example system prompt (fixed part) — kept in Italian, since the bot speaks Italian to customers:

```
Sei un esperto di giochi da tavolo molto empatico.
L'utente ha livello di esperienza: {expertise_level}.
Regole di comunicazione:
- Se beginner: usa linguaggio semplice, evita termini tecnici. Spiega sempre cosa significa
  una meccanica con esempi ("cooperativo significa che tutti giocano contro il gioco, non tra
  di voi, come in Pandemic").
- Se intermediate: puoi usare qualche termine ma spiegalo la prima volta.
- Se advanced: usa terminologia precisa (worker placement, engine building, area control, ecc.).

Non dare per scontato che conosca le cose.
Obiettivo: educare divertendo, mai far sentire stupido.
```

Example system prompt (dynamic part):

```
Hai a disposizione 4 strategie:
- GUIDED: usa esempi concreti di giochi + immagini. Massimo 1-2 scelte chiare alla volta.
  Ideale per utenti indecisi o molto principianti.
- EXPLANATORY: spiega le meccaniche con linguaggio semplice e analogie ("è come..."). Approfondisce
  quando l'utente mostra curiosità.
- DISCOVERY: stile libero e conversazionale. L'utente racconta cosa gli piacerebbe e tu proponi
  in modo creativo.
- QUICK MATCH: vai velocemente a proporre 3-4 giochi concreti quando l'utente è deciso.

Analisi attuale:
- Livello utente: {expertise_level}
- Informazioni raccolte: {structured_state}
- Stile risposte utente: {breve/lunga, entusiasta, indeciso, tecnico...}

Regole di transizione:
- Entusiasmo alto → privilegia DISCOVERY o EXPLANATORY.
- Entusiasmo basso o risposte brevi → passa a GUIDED o QUICK MATCH (proponi giochi concreti).
- Dopo max 3-4 scambi senza proposta concreta → passa obbligatoriamente a QUICK MATCH e fai
  retrieval di giochi.
```

Always analyze these aspects of the user: interest/enthusiasm (low/medium/high); decisiveness
(undecided / moderately / very decided); length and quality of the reply.

## Model tiering (chat)

We can evaluate tiers based on the conversation state and let, say, Haiku decide when/whether to
escalate to Sonnet based on conversation length, conversion potential, etc.

**Confidence-based escalation** (the simplest, recommended): Haiku includes a structured field
in its output:

```json
{
  "strategy": "GUIDED",
  "escalate_to_sonnet": true,
  "escalation_reason": "High complexity + user seems ready to buy (mentioned budget and player count)",
  "confidence": 0.82,
  "estimated_purchase_likelihood": "medium-high"
}
```

If `escalate_to_sonnet = true` → redo the call with Sonnet (or only the critical part: the final
recommendation generation).

**Hybrid router / classifier**: a small classifier (often Haiku itself or an even smaller model)
evaluates each turn, then decides the model for the reply.

**Tiered / multi-agent**: Haiku handles the normal conversation (fast and cheap); Sonnet steps in
only for: final recommendation generation; high-value users (e.g. high purchase history, cart >
X€, long session); complex interactions or when Haiku has low confidence.

## Absolute rules (anti-hallucination, RAG)

- You may name and recommend ONLY games present in the context provided under `<catalog>` or
  `<retrieved_games>`.
- If you find no suitable game in the catalog, answer honestly: "I don't currently have a game
  that matches perfectly, but here are the closest alternatives…" or offer to search for
  something else.
- Never use your prior knowledge of board games. Completely ignore everything you know outside the
  provided context.

Use structured output to improve the result.

### Known weakness — honest "we don't have it" is NOT working yet (seen 2026-06-18)

Observed in chat: a request for a *cooperative* game ("piace il cooperativo tipo Cronache di
Avel") gets pitched competitive titles (Wingspan/Catan/Carcassonne) **as if they matched** — the
honest-fallback rule above is simply not honored by the local 7-8B. To address. Skeleton stage,
much still to do on models/prompts/data.

Crucially, it is **not only a prompt problem** — the root cause is upstream, in retrieval:
- `nomic-embed-text` returns a flat similarity band (~0.65–0.69 across all 10 games) that does
  **not discriminate** the "cooperative" axis. A mismatched game (Wingspan, 0.708) can outscore
  the best hit of a genuinely cooperative query (Dixit, 0.685).
- The one truly cooperative game — Pandemic, **correctly tagged `Cooperativo`** (the tag does
  reach the LLM card) — ranked **#8/10** for a cooperative query, i.e. **outside k=5**, so the
  model never even sees it.
- Therefore a prompt-only "be honest, we don't have it" rule would **misfire**: it would deny a
  game we actually have, just un-retrieved. The honest framing can only be trusted once retrieval
  surfaces the right candidate.

Measured on a 10-game snapshot taken mid data-load; absolute ranks will shift as the catalog
grows, but the structural risk (embedder blind to the mechanic axis + hard `k` cutoff) persists.
Levers to revisit later: representation engineering / better embedder (see `valutazione.md` §2),
raise/tune `k`, a mechanic-aware filter or boost when the customer declares a mechanic, then layer
a code-enforced honest framing on top (don't trust the model's tone). Cross-ref `idee.md`.

## Model evaluations

Best local model to approximate Haiku (notes): a strong 7-9B instruct model in Q4_K_M / Q5_K_M
quantization (good tool calling, structured JSON output, reasoning and Italian; fits comfortably
in 8GB VRAM, full GPU offload possible). Valid alternatives: Llama 3.x 8B (more disciplined and
stable on long prompts and complex rules — good for the detailed system prompt); Gemma 9B (great
on structured output and tool use).

Definitely test the test-cases and checks at every phase of the process; having a JSON as input,
we can afford to generate test JSONs and test those heavily.

### Llama vs Qwen

Llama — pros: huge ecosystem, lots of LangChain/LangGraph examples, generally conservative and
predictable behavior, great to start with. Cons: at equal size often not the most performant,
tends to be more "rigid".

Qwen — pros: very good at following instructions, generally better at tool calling, often extracts
structured info better, many developers prefer it for agents. Cons: less documentation than Llama,
some versions can be a bit more verbose.

---

## Anthropic prompt caching (for when we move to the paid API)

Recorded idea, not urgent: when the Synth is on Sonnet/Haiku via the Anthropic API, enable prompt
caching to reduce the re-ingest cost. 90% discount on cached tokens (e.g. system prompt + closed
vocabularies).

**How it works** (NOT automatic — must be declared): you mark a prompt block with
`cache_control: {"type": "ephemeral"}`. The prefix up to that block is cached for 5 minutes from
the last use (there's also a 1h TTL, more expensive cache-write). Pricing on Haiku 4.5: normal
input $1/M, cache-write $1.25/M (+25%), cache-read $0.10/M (-90%).

**Real savings only if the cache stays WARM**: you need a dense **batch** ingest, not "one game at
a time scattered over time" (more than 5min without requests → cache expires → you only pay the
write surcharge for nothing).

**Preconditions to enable it**:
- the Synth prompt STABILIZED (changing it invalidates the cache)
- ingest organized as a batch job (daily/nightly cron, not on-arrival)
- separate in the prompt the STABLE block (system + vocab) from the VARIABLE block (the game's DTO)

**ROI estimate**: on 5,000 games/month it's the difference between ~$100-120/month (no cache) and
~$40/month (warm cache). Yearly: $700-1000/year saved. Not urgent while we work locally, but to
revisit as soon as we move to paid models.
