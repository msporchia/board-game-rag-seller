<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — ChatConversation — full multi-turn sessions

> case pass **0.867** · 15 conversations / 32 turns (convergence 0.846, fallback/turn 0.062) · 83 LLM calls / 93375 tok · model `qwen2.5:7b · engine=agent` · session 20260618-103413

```
  Conversations: 15   turns: 32   fallback/turn: 0.062 → (Δ +0.000, was: 0.062)
  LLM calls: 83 (Δ -3, was: 86)   (2.59/turn)   tokens: 93375 (Δ -6605, was: 99980)   (6225/conversation)

  case_pass          13/15 0.867 ↑ (Δ +0.067, was: 0.800)   [all conversations]
  convergence        11/13 0.846 ↑ (Δ +0.077, was: 0.769)   [cases with an accepted-games oracle]
  turn_oracles        4/5  0.800 ↓ (Δ -0.200, was: 1.000)   [declared per-turn checks]
  filters_ok            —     (no cases in scope: cases with a final-filters oracle)
  proposal_ok           —     (no cases in scope: cases with the forced-proposal oracle)
  mean turns to converge: 1.64

  ✓ terraforming-convergenza-vaga (converged turn 3)
  ✓ onitama-trappola-distrattore (converged turn 1)
  ✓ catan-assente-alternative (converged turn 1)
  ✓ azul-assente-alternative (converged turn 2)
  ✗ contrordine-giocatori: turn2:min_games, convergence (by turn 2)
  ✓ carcassonne-cliente-deciso (converged turn 1)
  ✓ stallo-proposta-forzata
  ✓ infeasibile-recupero
  ✓ bang-click-testo-misti (converged turn 1)
  ✗ pandemic-famiglia-cooperativo: convergence (by turn 2)
  ✓ deckbuilding-meccanica (converged turn 2)
  ✓ gestionale-worker-placement (converged turn 2)
  ✓ regalo-bambino-8anni (converged turn 2)
  ✓ horror-cooperativo (converged turn 1)
  ✓ trattative-diplomazia (converged turn 2)
```

## Failures (2)

### contrordine-giocatori
- failed:
  - turn2:min_games
  - convergence (by turn 2)
- cost: 4 LLM calls / 3928 tok
- trajectory:
  - 1. utente: cerco un gioco collaborativo da fare con i miei figli di 8 anni + click ['per 4 giocatori']
  -    search: «gioco cooperativo per famiglie» [filters: age={'max': 8}, players={'vals': [2]}] → 5 hits [3, 56, 32, 37, 40]
  -    [None] Fairy Tile, Fantascatti Special — bot: Ciao! Spero stiate bene e state per intraprendere un'avventura divertente con i vostri figli. Vado subito al punto: Fairy Tile è perfetto per le avventure fanta
  - 2. utente: anzi, ripensandoci i grandi non giocano quasi mai: meglio qualcosa che funzioni bene in due + click ['per 2 giocatori']
  -    [None] no games — bot: Al momento non ho in catalogo un gioco che corrisponde bene a quello che cerchi. Prova a dirmi qualcosa in più: quante persone giocano, quanto tempo avete, o un
- expected: accept_ids=[3, 48], by_turn=2, filters={'players': {'vals': [2]}}
- note: Constraint reversal: the turn-2 click must REPLACE the players filter (latest wins), not pile up — final filters_spec must say players=[2]. Family coop for an 8-year-old: both Pandemics (age 8, coop, 2 players ok); the age-14 horror coops are the confounders.

### pandemic-famiglia-cooperativo
- failed:
  - convergence (by turn 2)
- cost: 6 LLM calls / 7164 tok
- trajectory:
  - 1. utente: vorrei un gioco da fare con tutta la famiglia, i bambini hanno 8 anni
  -    search: «gioco per famiglie, adatto anche ai bambini di 8 anni, atmosfera festiva e coinvolgente» [filters: age={'max': 8}] → 5 hits [37, 52, 41, 56, 3]
  -    [None] Fantascatti Special, Dixit — bot: Ciao! Spero che tu stia bene. Stai cercando un gioco da tavolo perfetto per la famiglia, con i tuoi figli di 8 anni? Fantascatti Special è divertente e coinvolg
  - 2. utente: mi piacerebbe che si giocasse tutti insieme contro il gioco, senza vincitori e vinti, così non litigano
  -    search: «gioco cooperativo, si vince e si perde insieme» [filters: age={'max': 8}, duration={'max': 120}, players={'vals': [4]}] → 5 hits [3, 48, 56, 34, 40]
  -    [None] Fairy Tile, Carcassonne — bot: Ciao! Spero che tu stia bene. Stai cercando un gioco dove tutti giocano insieme, senza vincitori e vinti? Perfetto! Fairy Tile è fantastico per i bambini di 8 a
- expected: accept_ids=[3, 48], by_turn=2
- note: Constraints split across turns, no clicks: family-with-8-year-olds lives only in turn 1, the coop request only in turn 2. The query assembly must combine them to beat the six age-14 horror coops; both Pandemics are accepted.

## Passes (13)

- **terraforming-convergenza-vaga** — converged turn 3, cost 7 LLM calls / 8292 tok
  - 1. «ciao! cerco un gioco nuovo per il mio gruppo, siamo gioca…» → None: 8Bit Box, Talisman: Il Cataclisma
  - 2. «il tema che ci attira di più è la fantascienza» → None: no games
  - 3. «l'ideale sarebbe qualcosa dove costruisci un motore di ca…» → None: Terraforming Mars, Newton
- **onitama-trappola-distrattore** — converged turn 1, cost 6 LLM calls / 6619 tok
  - 1. «vorrei un gioco astratto da fare in due con mia figlia, p…» → None: Onitama, King of Tokyo
  - 2. «le piacciono molto le arti marziali: se il tema c'entra q…» → None: Onitama, Tao Long: Gioco da Tavolo Strategico per 2 Giocatori
- **catan-assente-alternative** — converged turn 1, cost 6 LLM calls / 7222 tok
  - 1. «avete Catan? volevo regalarlo a mio cugino» → None: Carcassonne, Fairy Tile
  - 2. «non c'è, eh? allora consigliami qualcosa di simile: costr…» → None: Clank!, Fairy Tile
- **azul-assente-alternative** — converged turn 2, cost 6 LLM calls / 6822 tok
  - 1. «sto cercando Azul, quello con le piastrelle colorate» → None: Clank!, Pandemic: 10th Anniversary
  - 2. «peccato! allora qualcosa di simile: piazzare tessere, ril…» → None: Fairy Tile, Onitama
- **carcassonne-cliente-deciso** — converged turn 1, cost 3 LLM calls / 3287 tok
  - 1. «avete Carcassonne? vorrei comprarlo, è per stasera» → None: Carcassonne, Solenia
- **stallo-proposta-forzata** — cost 4 LLM calls / 3176 tok
  - 1. «ciao, dovrei fare un regalo» → None: no games
  - 2. «mah, non saprei proprio cosa scegliere» → None: no games
  - 3. «boh, non so nemmeno io cosa gli piace» → None: no games
  - 4. «fai tu, mi fido» → None: no games
- **infeasibile-recupero** — cost 5 LLM calls / 4762 tok
  - 1. «in pausa pranzo io e un collega abbiamo solo cinque minut…» + click ['per 2 giocatori', 'max 5 minuti'] → None: no games
  - 2. «ok, in realtà possiamo arrivare a mezz'ora» + click ['max 30 minuti'] → None: Onitama, Tao Long: Gioco da Tavolo Strategico per 2 Giocatori
- **bang-click-testo-misti** — converged turn 1, cost 6 LLM calls / 6943 tok
  - 1. «sto organizzando una serata giochi con gli amici, vogliam…» → None: Fairy Tile, Overseers
  - 2. «ci piacciono i giochi dove si bluffa e magari qualcuno ha…» + click ['per 6 giocatori'] → None: Overseers, Citadels
- **deckbuilding-meccanica** — converged turn 2, cost 6 LLM calls / 7013 tok
  - 1. «cerco un gioco per il mio gruppo, siamo in tre o quattro …» → None: Overseers, 5 Minute Chase
  - 2. «in particolare adoriamo i giochi dove costruisci e potenz…» → None: Citadels, Newton
- **gestionale-worker-placement** — converged turn 2, cost 6 LLM calls / 6999 tok
  - 1. «siamo giocatori esperti e vogliamo un gestionale impegnat…» → None FALLBACK: Newton, Lords of Hellas, Solenia
  - 2. «ci piace soprattutto piazzare i lavoratori per raccoglier…» → None: Viticulture Essential Edition, Agricola
- **regalo-bambino-8anni** — converged turn 2, cost 6 LLM calls / 6485 tok
  - 1. «devo fare un regalo a un bambino di 8 anni, non gioca anc…» → None: Agricola, Viticulture Essential Edition
  - 2. «qualcosa di semplice e colorato, con regole che si spiega…» → None: Fantascatti Special, Fairy Tile
- **horror-cooperativo** — converged turn 1, cost 6 LLM calls / 6914 tok
  - 1. «vorremmo un gioco cooperativo per una serata a tema horro…» → None: Fireteam Zero, Massive Darkness
  - 2. «ci piace esplorare posti inquietanti e affrontare l'orror…» → None FALLBACK: Fireteam Zero, Le Case della Follia, Massive Darkness
- **trattative-diplomazia** — converged turn 2, cost 6 LLM calls / 7749 tok
  - 1. «cerchiamo un gioco dove si stringono alleanze e si tratta…» → None: Overseers, Terra Mystica
  - 2. «ci piace la politica, l'inganno e il tradimento al tavolo» → None: Schönbrunn, Overseers

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
