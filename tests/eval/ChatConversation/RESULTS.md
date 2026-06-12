<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — ChatConversation — full multi-turn sessions

> case pass **0.700** · 10 conversations / 22 turns (convergence 0.625, fallback/turn 0.000) · model `llama3.1` · session 20260612-094007

```
  Conversations: 10   turns: 22   fallback/turn: 0.000 ↓ (Δ -0.045, was: 0.045)

  case_pass           7/10 0.700 → (Δ +0.000, was: 0.700)   [all conversations]
  convergence         5/8  0.625 → (Δ +0.000, was: 0.625)   [cases with an accepted-games oracle]
  turn_oracles        6/6  1.000 → (Δ +0.000, was: 1.000)   [declared per-turn checks]
  filters_ok          3/3  1.000 → (Δ +0.000, was: 1.000)   [cases with a final-filters oracle]
  proposal_ok         1/1  1.000 → (Δ +0.000, was: 1.000)   [cases with the forced-proposal oracle]
  mean turns to converge: 1.2

  ✗ terraforming-convergenza-vaga: convergence (by turn 3)
  ✓ onitama-trappola-distrattore (converged turn 1)
  ✓ catan-assente-alternative (converged turn 1)
  ✓ azul-assente-alternative (converged turn 1)
  ✗ contrordine-giocatori: convergence (by turn 2)
  ✓ carcassonne-cliente-deciso (converged turn 1)
  ✓ stallo-proposta-forzata
  ✓ infeasibile-recupero
  ✓ bang-click-testo-misti (converged turn 2)
  ✗ pandemic-famiglia-cooperativo: convergence (by turn 2)
```

## Failures (3)

### terraforming-convergenza-vaga
- failed:
  - convergence (by turn 3)
- trajectory:
  - 1. utente: ciao! cerco un gioco nuovo per il mio gruppo, siamo giocatori esperti e ci piacciono i titoli impegnativi
  -    [GUIDED] Specie Dominanti, La Festa per Odino: I Norvegesi — bot: Ciao! Sembra che stiate cercando qualcosa di impegnativo per il vostro gruppo di giocatori esperti. Ecco due titoli che potrebbero interessarvi! Specie Dominant
  - 2. utente: il tema che ci attira di più è la fantascienza
  -    [GUIDED] Specie Dominanti, La Festa per Odino: I Norvegesi — bot: Fantascienza è un tema affascinante! Ho due titoli che potrebbero interessarvi, entrambi con una forte componente strategica e di gestione. Specie Dominanti vi 
  - 3. utente: l'ideale sarebbe qualcosa dove costruisci un motore di carte e risorse per rendere abitabile un pianeta
  -    [GUIDED ESC] Specie Dominanti — bot: Fantascienza è un tema affascinante! Sembra che stiate cercando qualcosa di impegnativo per il vostro gruppo di giocatori esperti. Ecco due titoli che potrebber
- expected: accept_ids=[21], by_turn=3
- note: Vague-to-specific convergence: heavy-gamer context (turn 1), sci-fi theme (turn 2), engine-building on a planet (turn 3). Terraforming Mars must surface by turn 3; Progetto Gaia, First Martians and Mercanti di Venere are the in-corpus sci-fi confounders.

### contrordine-giocatori
- failed:
  - convergence (by turn 2)
- trajectory:
  - 1. utente: cerco un gioco collaborativo da fare con i miei figli di 8 anni + click ['per 4 giocatori']
  -    [QUICK_MATCH] Fairy Tile, 8Bit Box, Dixit — bot: Benvenuto! Sono felice di aiutarti a trovare un gioco collaborativo per te e i tuoi figli. Ci sono alcuni giochi fantastici che potrebbero essere perfetti per v
  - 2. utente: anzi, ripensandoci i grandi non giocano quasi mai: meglio qualcosa che funzioni bene in due + click ['per 2 giocatori']
  -    [QUICK_MATCH] Fairy Tile, Fantascatti Special — bot: Hai cambiato idea sul numero dei giocatori! Non preoccuparti, ho trovato alcuni giochi che ti piaceranno anche con due giocatori. Fairy Tile è un'avventura fant
- expected: accept_ids=[3, 48], by_turn=2, filters={'players': {'vals': [2]}}
- final_filters: players={'vals': [2]}
- note: Constraint reversal: the turn-2 click must REPLACE the players filter (latest wins), not pile up — final filters_spec must say players=[2]. Family coop for an 8-year-old: both Pandemics (age 8, coop, 2 players ok); the age-14 horror coops are the confounders.

### pandemic-famiglia-cooperativo
- failed:
  - convergence (by turn 2)
- trajectory:
  - 1. utente: vorrei un gioco da fare con tutta la famiglia, i bambini hanno 8 anni
  -    [QUICK_MATCH] Fantascatti Special, Fairy Tile, Dixit — bot: Benvenuto! Sono felice di aiutarti a trovare il gioco perfetto per la tua famiglia! Fantascatti Special è un gioco divertente e interattivo che i bambini adorer
  - 2. utente: mi piacerebbe che si giocasse tutti insieme contro il gioco, senza vincitori e vinti, così non litigano
  -    [QUICK_MATCH] Fantascatti Special, Fairy Tile — bot: Fantastico! Sembra che stiate cercando un gioco da tavolo per la famiglia, dove tutti possano giocare insieme senza vincitori e vinti. Ho delle ottime proposte 
- expected: accept_ids=[3, 48], by_turn=2
- note: Constraints split across turns, no clicks: family-with-8-year-olds lives only in turn 1, the coop request only in turn 2. The query assembly must combine them to beat the six age-14 horror coops; both Pandemics are accepted.

## Passes (7)

- **onitama-trappola-distrattore** — converged turn 1
  - 1. «vorrei un gioco astratto da fare in due con mia figlia, p…» → QUICK_MATCH: Onitama, La Festa per Odino: I Norvegesi
  - 2. «le piacciono molto le arti marziali: se il tema c'entra q…» → QUICK_MATCH: Onitama, Kanagawa, Carcassonne
- **catan-assente-alternative** — converged turn 1
  - 1. «avete Catan? volevo regalarlo a mio cugino» → QUICK_MATCH: Carcassonne, Ticket to Ride: Europa, Citadels
  - 2. «non c'è, eh? allora consigliami qualcosa di simile: costr…» → QUICK_MATCH: Ticket to Ride: Europa, Solenia, Citadels
- **azul-assente-alternative** — converged turn 1
  - 1. «sto cercando Azul, quello con le piastrelle colorate» → QUICK_MATCH: Solenia, Carcassonne, Clank!
  - 2. «peccato! allora qualcosa di simile: piazzare tessere, ril…» → QUICK_MATCH: Onitama, Solenia, Orbis
- **carcassonne-cliente-deciso** — converged turn 1
  - 1. «avete Carcassonne? vorrei comprarlo, è per stasera» → QUICK_MATCH: Carcassonne, Orbis, Agricola
- **stallo-proposta-forzata**
  - 1. «ciao, dovrei fare un regalo» → GUIDED: Solenia, Ticket to Ride: Vagoni & Velieri
  - 2. «mah, non saprei proprio cosa scegliere» → GUIDED: Solenia, Ticket to Ride: Vagoni & Velieri
  - 3. «boh, non so nemmeno io cosa gli piace» → GUIDED: Solenia, Ticket to Ride: Vagoni & Velieri
  - 4. «fai tu, mi fido» → QUICK_MATCH: Solenia, Carcassonne
- **infeasibile-recupero**
  - 1. «in pausa pranzo io e un collega abbiamo solo cinque minut…» + click ['per 2 giocatori', 'max 5 minuti'] → QUICK_MATCH: no games
  - 2. «ok, in realtà possiamo arrivare a mezz'ora» + click ['max 30 minuti'] → QUICK_MATCH: Onitama, Tao Long: Gioco da Tavolo Strategico per 2 Giocatori, King of Tokyo
- **bang-click-testo-misti** — converged turn 2
  - 1. «sto organizzando una serata giochi con gli amici, vogliam…» → QUICK_MATCH: Fantascatti Special, Fairy Tile, Pandemic: 10th Anniversary, Specie Dominanti
  - 2. «ci piacciono i giochi dove si bluffa e magari qualcuno ha…» + click ['per 6 giocatori'] → QUICK_MATCH: Citadels, 8Bit Box, Fantascatti Special

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
