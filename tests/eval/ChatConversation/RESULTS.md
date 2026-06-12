<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — ChatConversation — full multi-turn sessions

> case pass **0.800** · 10 conversations / 22 turns (convergence 0.750, fallback/turn 0.000) · 47 LLM calls / 46726 tok · model `llama3.1 · engine=piloted` · session 20260612-112247

```
  Conversations: 10   turns: 22   fallback/turn: 0.000 → (Δ +0.000, was: 0.000)
  LLM calls: 47 (Δ +4, was: 43)   (2.14/turn)   tokens: 46726 (Δ -10266, was: 56992)   (4673/conversation)

  case_pass           8/10 0.800 ↑ (Δ +0.100, was: 0.700)   [all conversations]
  convergence         6/8  0.750 ↑ (Δ +0.125, was: 0.625)   [cases with an accepted-games oracle]
  turn_oracles        4/4  1.000 → (Δ +0.000, was: 1.000)   [declared per-turn checks]
  filters_ok          3/3  1.000 → (Δ +0.000, was: 1.000)   [cases with a final-filters oracle]
  proposal_ok           —     (no cases in scope: cases with the forced-proposal oracle)
  mean turns to converge: 1.5

  ✓ terraforming-convergenza-vaga (converged turn 2)
  ✓ onitama-trappola-distrattore (converged turn 1)
  ✓ catan-assente-alternative (converged turn 2)
  ✓ azul-assente-alternative (converged turn 1)
  ✓ contrordine-giocatori (converged turn 1)
  ✗ carcassonne-cliente-deciso: convergence (by turn 1)
  ✓ stallo-proposta-forzata
  ✓ infeasibile-recupero
  ✓ bang-click-testo-misti (converged turn 2)
  ✗ pandemic-famiglia-cooperativo: convergence (by turn 2)
```

## Failures (2)

### carcassonne-cliente-deciso
- failed:
  - convergence (by turn 1)
- cost: 2 LLM calls / 1765 tok
- trajectory:
  - 1. utente: avete Carcassonne? vorrei comprarlo, è per stasera
  -    search: «gioco strategico per due persone con una durata di circa mezz'ora» [filters: duration={'max': 30}, players={'vals': [2]}] → 5 hits
  -    [None] Spirits of the Forest, King of Tokyo — bot: Ciao! Sembra che tu stia cercando un gioco per giocare con qualcuno questa sera. Ho alcuni consigli che potrebbero piacerti! Spirits of the Forest è un gioco di
- expected: accept_ids=[34], by_turn=1
- note: Decided customer at turn 1: a precise title plus purchase intent must route straight to QUICK_MATCH (no useless GUIDED loop) and put Carcassonne on the table immediately. Likely escalate=true too (purchase intent) — recorded in the trajectory.

### pandemic-famiglia-cooperativo
- failed:
  - convergence (by turn 2)
- cost: 4 LLM calls / 4286 tok
- trajectory:
  - 1. utente: vorrei un gioco da fare con tutta la famiglia, i bambini hanno 8 anni
  -    search: «gioco da tavolo per famiglie con bambini di 8 anni, gioco cooperativo, si vince e si perde insieme» [filters: age={'max': 8}, duration={'max': 60}, players={'vals': [4]}] → 5 hits
  -    [None] Fairy Tile, Fantascatti Special, Dixit — bot: Ciao! Sono felice di aiutarti a trovare un gioco da tavolo adatto per la tua famiglia! I bambini hanno 8 anni, quindi cercherò giochi divertenti e facili da cap
  - 2. utente: mi piacerebbe che si giocasse tutti insieme contro il gioco, senza vincitori e vinti, così non litigano
  -    search: «gioco cooperativo per famiglie con bambini di 8 anni, senza vincitori e vinti» [filters: age={'max': 8}, duration={'max': 60}, players={'vals': [4]}] → 5 hits
  -    [None] Fairy Tile, Fantascatti Special — bot: Ciao! Sembra che tu stia cercando un gioco da tavolo per la tua famiglia, dove i bambini di 8 anni possano giocare tutti insieme contro il gioco senza vincitori
- expected: accept_ids=[3, 48], by_turn=2
- note: Constraints split across turns, no clicks: family-with-8-year-olds lives only in turn 1, the coop request only in turn 2. The query assembly must combine them to beat the six age-14 horror coops; both Pandemics are accepted.

## Passes (8)

- **terraforming-convergenza-vaga** — converged turn 2, cost 6 LLM calls / 7554 tok
  - 1. «ciao! cerco un gioco nuovo per il mio gruppo, siamo gioca…» → None: Terra Mystica, La Festa per Odino: I Norvegesi, Progetto Gaia
  - 2. «il tema che ci attira di più è la fantascienza» → None: First Martians, Terraforming Mars, Amun-Re
  - 3. «l'ideale sarebbe qualcosa dove costruisci un motore di ca…» → None: Terraforming Mars, Progetto Gaia
- **onitama-trappola-distrattore** — converged turn 1, cost 4 LLM calls / 4138 tok
  - 1. «vorrei un gioco astratto da fare in due con mia figlia, p…» → None: Onitama, Tao Long: Gioco da Tavolo Strategico per 2 Giocatori
  - 2. «le piacciono molto le arti marziali: se il tema c'entra q…» → None: Onitama, Tao Long: Gioco da Tavolo Strategico per 2 Giocatori, Fairy Tile
- **catan-assente-alternative** — converged turn 2, cost 4 LLM calls / 3953 tok
  - 1. «avete Catan? volevo regalarlo a mio cugino» → None: Onitama, Fairy Tile
  - 2. «non c'è, eh? allora consigliami qualcosa di simile: costr…» → None: Carcassonne, Solenia
- **azul-assente-alternative** — converged turn 1, cost 4 LLM calls / 4164 tok
  - 1. «sto cercando Azul, quello con le piastrelle colorate» → None: Fairy Tile, Pot de Vin
  - 2. «peccato! allora qualcosa di simile: piazzare tessere, ril…» → None: Orbis, Carcassonne, Solenia
- **contrordine-giocatori** — converged turn 1, cost 4 LLM calls / 4216 tok
  - 1. «cerco un gioco collaborativo da fare con i miei figli di …» + click ['per 4 giocatori'] → None: Fairy Tile, Pandemic: 10th Anniversary
  - 2. «anzi, ripensandoci i grandi non giocano quasi mai: meglio…» + click ['per 2 giocatori'] → None: Fairy Tile, Fantascatti Special
- **stallo-proposta-forzata** — cost 11 LLM calls / 9720 tok
  - 1. «ciao, dovrei fare un regalo» → None: Fairy Tile, Fantascatti Special
  - 2. «mah, non saprei proprio cosa scegliere» → None: Citadels, Fairy Tile
  - 3. «boh, non so nemmeno io cosa gli piace» → None: Fairy Tile, King of Tokyo
  - 4. «fai tu, mi fido» → None: King of Tokyo, Citadels, Onitama
- **infeasibile-recupero** — cost 4 LLM calls / 2696 tok
  - 1. «in pausa pranzo io e un collega abbiamo solo cinque minut…» + click ['per 2 giocatori', 'max 5 minuti'] → None: no games
  - 2. «ok, in realtà possiamo arrivare a mezz'ora» + click ['max 30 minuti'] → None: Onitama, 5 Minute Chase
- **bang-click-testo-misti** — converged turn 2, cost 4 LLM calls / 4234 tok
  - 1. «sto organizzando una serata giochi con gli amici, vogliam…» → None: Ticket to Ride: Europa, Solenia, Fairy Tile
  - 2. «ci piacciono i giochi dove si bluffa e magari qualcuno ha…» + click ['per 6 giocatori'] → None: Overseers, Citadels

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
