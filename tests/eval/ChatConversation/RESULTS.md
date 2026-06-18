<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — ChatConversation — full multi-turn sessions

> case pass **0.600** · 10 conversations / 22 turns (convergence 0.500, fallback/turn 0.000) · 55 LLM calls / 62358 tok · model `llama3.1 · engine=agent` · session 20260618-101657

```
  Conversations: 10   turns: 22   fallback/turn: 0.000 → (Δ +0.000, was: 0.000)
  LLM calls: 55 (Δ +8, was: 47)   (2.5/turn)   tokens: 62358 (Δ +15632, was: 46726)   (6236/conversation)

  case_pass           6/10 0.600 ↓ (Δ -0.200, was: 0.800)   [all conversations]
  convergence         4/8  0.500 ↓ (Δ -0.250, was: 0.750)   [cases with an accepted-games oracle]
  turn_oracles        3/4  0.750 ↓ (Δ -0.250, was: 1.000)   [declared per-turn checks]
  filters_ok            —     (no cases in scope: cases with a final-filters oracle)
  proposal_ok           —     (no cases in scope: cases with the forced-proposal oracle)
  mean turns to converge: 1.25

  ✓ terraforming-convergenza-vaga (converged turn 2)
  ✓ onitama-trappola-distrattore (converged turn 1)
  ✓ catan-assente-alternative (converged turn 1)
  ✓ azul-assente-alternative (converged turn 1)
  ✗ contrordine-giocatori: turn2:min_games, convergence (by turn 2)
  ✗ carcassonne-cliente-deciso: convergence (by turn 1)
  ✓ stallo-proposta-forzata
  ✓ infeasibile-recupero
  ✗ bang-click-testo-misti: convergence (by turn 2)
  ✗ pandemic-famiglia-cooperativo: convergence (by turn 2)
```

## Failures (4)

### contrordine-giocatori
- failed:
  - turn2:min_games
  - convergence (by turn 2)
- cost: 4 LLM calls / 3882 tok
- trajectory:
  - 1. utente: cerco un gioco collaborativo da fare con i miei figli di 8 anni + click ['per 4 giocatori']
  -    search: «gioco cooperativo per famiglie» [filters: age={'max': 8}, players={'vals': [2]}] → 5 hits [3, 56, 32, 37, 40]
  -    [None] Fairy Tile, Fantascatti Special — bot: Ciao! Sono felice di aiutarti a scegliere un gioco perfetto per voi due. Cerchiamo qualcosa di divertente e coinvolgente, giusto? Fairy Tile è un gioco fantasti
  - 2. utente: anzi, ripensandoci i grandi non giocano quasi mai: meglio qualcosa che funzioni bene in due + click ['per 2 giocatori']
  -    [None] no games — bot: Al momento non ho in catalogo un gioco che corrisponde bene a quello che cerchi. Prova a dirmi qualcosa in più: quante persone giocano, quanto tempo avete, o un
- expected: accept_ids=[3, 48], by_turn=2, filters={'players': {'vals': [2]}}
- note: Constraint reversal: the turn-2 click must REPLACE the players filter (latest wins), not pile up — final filters_spec must say players=[2]. Family coop for an 8-year-old: both Pandemics (age 8, coop, 2 players ok); the age-14 horror coops are the confounders.

### carcassonne-cliente-deciso
- failed:
  - convergence (by turn 1)
- cost: 3 LLM calls / 3103 tok
- trajectory:
  - 1. utente: avete Carcassonne? vorrei comprarlo, è per stasera
  -    search: «gioco di carte, costruzione, si vince e si perde insieme» [filters: duration={'max': 180}, players={'vals': [2]}] → 5 hits [47, 28, 33, 56, 39]
  -    [None] La Festa per Odino: I Norvegesi, Fairy Tile — bot: Ciao! Spero che stasera tu abbia un appuntamento speciale. Ti consiglio due giochi perfetti per la serata. La Festa per Odino: I Norvegesi è una bella avventura
- expected: accept_ids=[34], by_turn=1
- note: Decided customer at turn 1: a precise title plus purchase intent must route straight to QUICK_MATCH (no useless GUIDED loop) and put Carcassonne on the table immediately. Likely escalate=true too (purchase intent) — recorded in the trajectory.

### bang-click-testo-misti
- failed:
  - convergence (by turn 2)
- cost: 4 LLM calls / 4400 tok
- trajectory:
  - 1. utente: sto organizzando una serata giochi con gli amici, vogliamo soprattutto ridere
  -    search: «gioco cooperativo, si vince e si perde insieme» [filters: none] → 5 hits [3, 10, 48, 56, 11]
  -    [None] Fairy Tile, Pandemic: 10th Anniversary — bot: Ciao! Sono felice di aiutarti a scegliere un gioco per la serata in cui volete solo ridere con gli amici. Fireteam Zero è perfetto per una serata divertente. Co
  - 2. utente: ci piacciono i giochi dove si bluffa e magari qualcuno ha un ruolo nascosto + click ['per 6 giocatori']
  -    [None] no games — bot: Al momento non ho in catalogo un gioco che corrisponde bene a quello che cerchi. Prova a dirmi qualcosa in più: quante persone giocano, quanto tempo avete, o un
- expected: accept_ids=[51, 42, 44], by_turn=2, filters={'players': {'vals': [6]}}
- note: Clicks and free text mixed: the click becomes the hard players filter while the bluff/hidden-roles request rides the query. Accepted: BANG! Deluxe (the humor+bluff ideal), Citadels, Overseers (bluff games seating 6).

### pandemic-famiglia-cooperativo
- failed:
  - convergence (by turn 2)
- cost: 6 LLM calls / 7225 tok
- trajectory:
  - 1. utente: vorrei un gioco da fare con tutta la famiglia, i bambini hanno 8 anni
  -    search: «gioco per famiglie, adatto anche ai bambini di 8 anni, atmosfera divertente e coinvolgente» [filters: age={'max': 8}] → 5 hits [37, 52, 41, 56, 51]
  -    [None] Fantascatti Special, Dixit — bot: Ciao! Spero stiate bene. Sto cercando il gioco perfetto per divertirvi tutta la famiglia, specialmente con i bambini che hanno 8 anni. Ti aiuto a scegliere! Fan
  - 2. utente: mi piacerebbe che si giocasse tutti insieme contro il gioco, senza vincitori e vinti, così non litigano
  -    search: «gioco cooperativo, si vince e si perde insieme» [filters: age={'max': 8}, duration={'max': 180}, players={'vals': [4]}] → 5 hits [3, 48, 56, 34, 40]
  -    [None] Fairy Tile, Carcassonne — bot: Ciao! Spero stiate bene. Sto cercando un gioco dove tutti giocate insieme, senza vincitori e vinti? Ci sono diverse opzioni fantastiche per la vostra famiglia! 
- expected: accept_ids=[3, 48], by_turn=2
- note: Constraints split across turns, no clicks: family-with-8-year-olds lives only in turn 1, the coop request only in turn 2. The query assembly must combine them to beat the six age-14 horror coops; both Pandemics are accepted.

## Passes (6)

- **terraforming-convergenza-vaga** — converged turn 2, cost 7 LLM calls / 8345 tok
  - 1. «ciao! cerco un gioco nuovo per il mio gruppo, siamo gioca…» → None: Altiplano di Giochix, Amun-Re
  - 2. «il tema che ci attira di più è la fantascienza» → None: First Martians, Terraforming Mars
  - 3. «l'ideale sarebbe qualcosa dove costruisci un motore di ca…» → None: no games
- **onitama-trappola-distrattore** — converged turn 1, cost 6 LLM calls / 6781 tok
  - 1. «vorrei un gioco astratto da fare in due con mia figlia, p…» → None: Onitama, Tao Long: Gioco da Tavolo Strategico per 2 Giocatori
  - 2. «le piacciono molto le arti marziali: se il tema c'entra q…» → None: Onitama, Kanagawa
- **catan-assente-alternative** — converged turn 1, cost 6 LLM calls / 7389 tok
  - 1. «avete Catan? volevo regalarlo a mio cugino» → None: Carcassonne, Solenia
  - 2. «non c'è, eh? allora consigliami qualcosa di simile: costr…» → None: Carcassonne, Solenia
- **azul-assente-alternative** — converged turn 1, cost 6 LLM calls / 6908 tok
  - 1. «sto cercando Azul, quello con le piastrelle colorate» → None: Clank!, Kanagawa
  - 2. «peccato! allora qualcosa di simile: piazzare tessere, ril…» → None: 5 Minute Chase, Star Wars: Legion
- **stallo-proposta-forzata** — cost 8 LLM calls / 9543 tok
  - 1. «ciao, dovrei fare un regalo» → None: no games
  - 2. «mah, non saprei proprio cosa scegliere» → None: no games
  - 3. «boh, non so nemmeno io cosa gli piace» → None: Onitama, 5 Minute Chase, Agricola
  - 4. «fai tu, mi fido» → None: Fairy Tile, Tao Long: Gioco da Tavolo Strategico per 2 Giocatori
- **infeasibile-recupero** — cost 5 LLM calls / 4782 tok
  - 1. «in pausa pranzo io e un collega abbiamo solo cinque minut…» + click ['per 2 giocatori', 'max 5 minuti'] → None: no games
  - 2. «ok, in realtà possiamo arrivare a mezz'ora» + click ['max 30 minuti'] → None: Onitama, Tao Long: Gioco da Tavolo Strategico per 2 Giocatori

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
