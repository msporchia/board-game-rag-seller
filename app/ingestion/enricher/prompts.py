"""All ingestion-enricher prompt text, in ONE place (the ingestion-layer twin of
`app/chat/prompts.py`). The enrichers keep only the COMPOSITION logic — which labels to ask, the
description truncation, the word budget — while the TEXT lives here as `{placeholder}` templates
they `.format()`.

Intentionally Italian: they drive an Italian-language LLM over an Italian catalog (CLAUDE.md), so
they are not translated. Literal braces in the JSON examples are doubled (`{{ }}`) for `.format()`.

Sections: CuratorEnricher (cooperative inference · label extraction) · WebEnricher (judge+extract)
· SynthEnricher (description synthesis).
"""

# ── CuratorEnricher ───────────────────────────────────────────────────────────

# Cooperative play-mode inference (SEL-142): a reasoned classification of the meaning, NOT a
# keyword hunt. Template: {desc}.
COOP_INFER = """Sei un esperto di giochi da tavolo. In base alla DESCRIZIONE, stabilisci la
MODALITÀ di gioco RAGIONANDO sul significato (non cercare solo la parola "cooperativo"):
- "cooperativo": i giocatori giocano INSIEME contro il gioco, si vince o si perde tutti insieme;
- "competitivo": i giocatori giocano l'UNO CONTRO L'ALTRO;
- "incerto": la descrizione non basta per stabilirlo con certezza.

DESCRIZIONE:
{desc}

Rispondi SOLO con JSON: {{"modalita": "cooperativo" | "competitivo" | "incerto"}}"""

# Focused label extraction: only the LABELS we need, only the DESCRIPTION (no certain data — we
# apply those downstream, they always win). Template: {count}, {bullet}, {description}.
CURATOR_EXTRACT = """Compito: per OGNI etichetta della LISTA estrai dalla DESCRIZIONE il
valore richiesto. Anti-invenzione: se non puoi copiare una citazione VERBATIM dalla
DESCRIZIONE che lo dimostri, scrivi "NESSUNO".

ETICHETTE da analizzare (esattamente {count}, nell'ordine):
{bullet}

Per OGNI etichetta produci un oggetto con questi campi:
- "citazione": testo VERBATIM (max 80 caratteri) copiato dalla DESCRIZIONE. DEVE essere
  copiato letteralmente — sarà verificato a valle. Stringa vuota se non c'è.
- "valore_normalizzato": valore breve e normalizzato (es. "fantasy", "mitologia greca",
  "cooperativo", "famiglie", "120 minuti", "1-4", "media"). Stringa "NESSUNO" se non si
  riesce a citare.

Regole rigide:
- Se la DESCRIZIONE non contiene esplicitamente l'informazione → "valore_normalizzato":
  "NESSUNO" e "citazione": "". NON inferire dal tono o dall'atmosfera.
- "numero giocatori" si estrae SOLO se c'è un numero/range esplicito (es. "2 a 4
  giocatori"). NON inferire dal genere o da "famiglia".
- "durata" si estrae SOLO se c'è un numero esplicito di minuti/ore. Non aggiungere range
  "verosimili".

DESCRIZIONE:
{description}

Rispondi SOLO con JSON, una chiave per ogni etichetta della LISTA:
{{"<etichetta1>": {{"citazione":"...","valore_normalizzato":"..."}},
  "<etichetta2>": {{...}}, ...}}"""

# ── WebEnricher ───────────────────────────────────────────────────────────────

# Judge a fetched web page AND extract only the missing facts, each with a verbatim quote (the
# anti-fabrication gate). Template: {name} (twice), {aspects}, {text}.
WEB_JUDGE_EXTRACT = """Sei un redattore di giochi da tavolo. Ricevi il TESTO di una pagina web
e devi giudicarla ed estrarne informazioni sul gioco "{name}".

Regole rigide (zero invenzioni):
- Estrai un'informazione SOLO se è ESPLICITA nel testo. Per ognuna fornisci una CITAZIONE
  verbatim (`quote`) copiata ESATTAMENTE dal testo (serve a verificarti).
- Se un'informazione non c'è, NON includerla. Mai dedurre o usare conoscenza tua.
- `is_this_game`: il testo parla DAVVERO del gioco "{name}" (non un omonimo/altro gioco)?
- `is_serious`: è una recensione/scheda informativa (non un mero elenco prodotti di un negozio)?

Estrai SOLO queste informazioni mancanti, se presenti: {aspects}.

Rispondi SOLO con JSON valido in questo formato:
{{"is_this_game": true/false, "is_serious": true/false,
  "found": {{"<info>": {{"value": "...", "quote": "...verbatim dal testo..."}}}}}}

TESTO:
{text}
"""

# ── SynthEnricher ─────────────────────────────────────────────────────────────

# Synthesize ONE dense experiential description from all the material (numeric data lives
# elsewhere — do not repeat it). Template: {name}, {min_words}, {max_words}, {material}.
# v2 (SEL-144): searchable-concepts checklist + explicit ban on could-be-any-game phrasing —
# the synth normalizes the FORMAT while maximizing per-game distinctiveness of the content.
SYNTH_DESCRIPTION = """Sei un redattore di giochi da tavolo. Scrivi UNA sintesi descrittiva e densa
del gioco "{name}", basandoti ESCLUSIVAMENTE sul materiale qui sotto.

A cosa serve: questo testo è ciò che il motore di ricerca semantica "vede" del gioco. Un cliente
lo troverà cercando concetti ("un cooperativo per la famiglia", "un gestionale sul vino in
Toscana"): la sintesi deve contenere, con parole precise, TUTTI i concetti cercabili presenti nel
materiale. I dati numerici (giocatori, durata, complessità, anno) sono registrati ALTROVE: NON
ripeterli.

Copri, se presenti nel materiale, in quest'ordine:
1. Le meccaniche di gioco coi loro nomi precisi ("piazzamento lavoratori", "deck-building",
   "cooperativo", "aste"...) e cosa si fa concretamente durante il proprio turno.
2. Ambientazione e tema, coi nomi propri (luoghi, epoche, personaggi, divinità...).
3. A chi è adatto e per quale occasione (famiglia, esperti, serata tra amici, in coppia...).
4. Tono ed esperienza (teso e competitivo, rilassato, narrativo, umoristico...).

Regole rigide:
- USA le parole distintive del materiale. VIETATE le frasi che andrebbero bene per qualunque
  gioco ("esperienza coinvolgente", "divertimento assicurato", "mette alla prova le tue
  abilità", "trasporta i giocatori in un mondo..."): ogni frase deve distinguere QUESTO gioco
  dagli altri.
- NON indicare numero di giocatori, durata in minuti, complessità o anno: sono aggiunti a parte.
- Usa SOLO fatti presenti nel materiale. NON inventare nulla. Se un'informazione non c'è, non
  scriverla. I [DATI CERTI] danno solo il contesto: non contraddirli.
- Togli il marketing vuoto: esclamazioni, inviti all'acquisto, superlativi senza contenuto.
- Stile: prosa scorrevole, niente elenchi né titoli. Circa {min_words}-{max_words} parole.

MATERIALE:
{material}

Rispondi SOLO con la sintesi, senza preamboli."""
