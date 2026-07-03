<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — ChatConversation — full multi-turn sessions

> case pass **0.733** · 15 conversations / 32 turns (convergence 0.769, fallback/turn 0.062) · 81 LLM calls / 92599 tok · model `qwen2.5:7b · engine=agent` · session 20260703-133501

```
  Conversations: 15   turns: 32   fallback/turn: 0.062 ↑ (Δ +0.062, was: 0.000)
  LLM calls: 81 (Δ +18, was: 63)   (2.53/turn)   tokens: 92599 (Δ +8982, was: 83617)   (6173/conversation)

  case_pass          11/15 0.733 ↑ (Δ +0.067, was: 0.667)   [all conversations]
  convergence        10/13 0.769 ↑ (Δ +0.154, was: 0.615)   [cases with an accepted-games oracle]
  turn_oracles        4/5  0.800 ↓ (Δ -0.200, was: 1.000)   [declared per-turn checks]
  filters_ok            —     (no cases in scope: cases with a final-filters oracle)
  proposal_ok           —     (no cases in scope: cases with the forced-proposal oracle)
  mean turns to converge: 1.4

  ✗ terraforming-convergenza-vaga: convergence (by turn 3)
  ✗ onitama-trappola-distrattore: convergence (by turn 2)
  ✓ catan-assente-alternative (converged turn 2)
  ✓ azul-assente-alternative (converged turn 1)
  ✗ contrordine-giocatori: turn2:min_games
  ✓ carcassonne-cliente-deciso (converged turn 1)
  ✓ stallo-proposta-forzata
  ✓ infeasibile-recupero
  ✓ bang-click-testo-misti (converged turn 1)
  ✓ pandemic-famiglia-cooperativo (converged turn 1)
  ✓ deckbuilding-meccanica (converged turn 2)
  ✓ gestionale-worker-placement (converged turn 2)
  ✓ regalo-bambino-8anni (converged turn 2)
  ✓ horror-cooperativo (converged turn 1)
  ✗ trattative-diplomazia: convergence (by turn 2)
```

## Failures (4)

### terraforming-convergenza-vaga
- failed:
  - convergence (by turn 3)
- cost: 9 LLM calls / 12615 tok
- trajectory:
  - 1. utente: ciao! cerco un gioco nuovo per il mio gruppo, siamo giocatori esperti e ci piacciono i titoli impegnativi
  -    search: «gioco per giocatori esperti, meccaniche complesse, esperienza impegnativa» [filters: players={'vals': [4]}] → 5 hits [27, 1, 33, 25, 22]
  -    [None] Clank!, Through the Ages, Newton — bot: Ciao! Siamo entusiasti di aiutarti a trovare un gioco nuovo per voi esperti giocatori. Vi piacciono giochi impegnativi e coinvolgenti? Clank! è un gioco avventu
  - 2. utente: il tema che ci attira di più è la fantascienza
  -    search: «gioco fantascienza» [filters: none] → 5 hits [1, 35, 28, 27, 50]
  -    [None] Massive Darkness, Talisman — bot: Ciao! Sembra che stiate cercando un gioco di fantascienza coinvolgente. Ho trovato alcuni titoli che potrebbero interessarvi. Massive Darkness è un gioco cooper
  - 3. utente: l'ideale sarebbe qualcosa dove costruisci un motore di carte e risorse per rendere abitabile un pianeta
  -    search: «costruzione di carte e risorse, avventura spaziale» [filters: cooperative={'val': True}, players={'vals': [2]}] → 5 hits [10, 1, 11, 4, 48]
  -    [None] First Martians, Massive Darkness — bot: Ciao! Sembra che stiate cercando un gioco di fantascienza dove costruirete un motore di carte e risorse per rendere abitabile un pianeta. Ho trovato un gioco pe
- expected: accept_ids=[21], by_turn=3
- note: Vague-to-specific convergence: heavy-gamer context (turn 1), sci-fi theme (turn 2), engine-building on a planet (turn 3). Terraforming Mars must surface by turn 3; Progetto Gaia, First Martians and Mercanti di Venere are the in-corpus sci-fi confounders.

### onitama-trappola-distrattore
- failed:
  - convergence (by turn 2)
- cost: 5 LLM calls / 5292 tok
- trajectory:
  - 1. utente: vorrei un gioco astratto da fare in due con mia figlia, partite brevi
  -    search: «gioco astratto per 2 persone, partite brevi» [filters: age={'max': 8}, cooperative={'val': False}, duration={'max': 30}, players={'vals': [2]}] → 0 hits
  -    [None] no games — bot: Al momento non ho in catalogo un gioco che corrisponde bene a quello che cerchi. Prova a dirmi qualcosa in più: quante persone giocano, quanto tempo avete, o un
  - 2. utente: le piacciono molto le arti marziali: se il tema c'entra qualcosa è perfetto
  -    search: «tema arti marziali, gioco astratto» [filters: age={'max': 8}, duration={'max': 30}, players={'vals': [2]}] → 4 hits [32, 37, 54, 56]
  -    [None] 5 Minute Chase, King of Tokyo — bot: Ciao! Sembra che tu stia cercando un gioco divertente per te e tua figlia, magari con un tema di arti marziali. Vediamo insieme cosa abbiamo in catalogo! 5 Minu
- expected: accept_ids=[160], by_turn=2
- note: Distractor trap: turn 1 alone matches Tao Long and Spirits of the Forest just as well (2p abstract, short). The martial-arts detail of turn 2 must re-rank toward Onitama — measures that the assembled query carries the NEW detail without losing the old constraints.

### contrordine-giocatori
- failed:
  - turn2:min_games
- cost: 4 LLM calls / 3973 tok
- trajectory:
  - 1. utente: cerco un gioco collaborativo da fare con i miei figli di 8 anni + click ['per 4 giocatori']
  -    search: «gioco cooperativo, adatto ai bambini» [filters: age={'max': 8}, cooperative={'val': True}, players={'vals': [2]}] → 2 hits [48, 3]
  -    [None] Pandemic: 10th Anniversary, Pandemic: La Caduta di Roma — bot: Ciao! Sono felice di aiutarti a scegliere un gioco perfetto per i tuoi figli. Abbiamo due opzioni davvero interessanti oggi. Pandemic: 10th Anniversary è un gio
  - 2. utente: anzi, ripensandoci i grandi non giocano quasi mai: meglio qualcosa che funzioni bene in due + click ['per 2 giocatori']
  -    [None] no games — bot: Al momento non ho in catalogo un gioco che corrisponde bene a quello che cerchi. Prova a dirmi qualcosa in più: quante persone giocano, quanto tempo avete, o un
- expected: accept_ids=[3, 48], by_turn=2, filters={'players': {'vals': [2]}}
- note: Constraint reversal: the turn-2 click must REPLACE the players filter (latest wins), not pile up — final filters_spec must say players=[2]. Family coop for an 8-year-old: both Pandemics (age 8, coop, 2 players ok); the age-14 horror coops are the confounders.

### trattative-diplomazia
- failed:
  - convergence (by turn 2)
- cost: 6 LLM calls / 5646 tok
- trajectory:
  - 1. utente: cerchiamo un gioco dove si stringono alleanze e si tratta tra giocatori, siamo in cinque
  -    search: «gioco con alleanze tra i giocatori» [filters: cooperative={'val': False}, players={'vals': [5]}] → 1 hits [28]
  -    [None] Talisman: Il Cataclisma — bot: Ciao! Siamo in cinque a giocare, giusto? Volete formare alleanze e affrontare sfide insieme. Ti propongo due opzioni che potrebbero piacerti molto. Talisman: Il
  - 2. utente: ci piace la politica, l'inganno e il tradimento al tavolo
  -    search: «gioco con politica inganno tradimento» [filters: cooperative={'val': False}, players={'vals': [5]}] → 1 hits [28]
  -    [None] Talisman: Il Cataclisma — bot: Ciao! Volete giocare a qualcosa che coinvolge politica, inganno e un po' di tradimento? Siamo in cinque, giusto? Talisman: Il Cataclisma è perfetto per voi. Vi 
- expected: accept_ids=[31, 38], by_turn=2
- note: Negotiation / politics dimension (not covered elsewhere): alliances + bargaining + betrayal, 5 players. Il Trono di Spade (politics, negotiation, alliances, bluff; 3-6) and Schönbrunn (diplomatic bargaining; 3-6) are accepted; auction euros like Amun-Re are the near-miss.

## Passes (11)

- **catan-assente-alternative** — converged turn 2, cost 6 LLM calls / 6515 tok
  - 1. «avete Catan? volevo regalarlo a mio cugino» → None: Talisman: Il Cataclisma
  - 2. «non c'è, eh? allora consigliami qualcosa di simile: costr…» → None: Puerto Rico, Through the Ages
- **azul-assente-alternative** — converged turn 1, cost 5 LLM calls / 5615 tok
  - 1. «sto cercando Azul, quello con le piastrelle colorate» → None: Fairy Tile, 5 Minute Chase
  - 2. «peccato! allora qualcosa di simile: piazzare tessere, ril…» → None: no games
- **carcassonne-cliente-deciso** — converged turn 1, cost 3 LLM calls / 3311 tok
  - 1. «avete Carcassonne? vorrei comprarlo, è per stasera» → None: Carcassonne, Near and Far
- **stallo-proposta-forzata** — cost 8 LLM calls / 10221 tok
  - 1. «ciao, dovrei fare un regalo» → None: no games
  - 2. «mah, non saprei proprio cosa scegliere» → None: no games
  - 3. «boh, non so nemmeno io cosa gli piace» → None: Fairy Tile, Carcassonne
  - 4. «fai tu, mi fido» → None: Fairy Tile, Le Case della Follia
- **infeasibile-recupero** — cost 5 LLM calls / 5224 tok
  - 1. «in pausa pranzo io e un collega abbiamo solo cinque minut…» + click ['per 2 giocatori', 'max 5 minuti'] → None: no games
  - 2. «ok, in realtà possiamo arrivare a mezz'ora» + click ['max 30 minuti'] → None: 5 Minute Chase, Onitama
- **bang-click-testo-misti** — converged turn 1, cost 4 LLM calls / 4570 tok
  - 1. «sto organizzando una serata giochi con gli amici, vogliam…» → None: Dixit, BANG! Deluxe
  - 2. «ci piacciono i giochi dove si bluffa e magari qualcuno ha…» + click ['per 6 giocatori'] → None: no games
- **pandemic-famiglia-cooperativo** — converged turn 1, cost 4 LLM calls / 4079 tok
  - 1. «vorrei un gioco da fare con tutta la famiglia, i bambini …» → None: Pandemic: 10th Anniversary, Pandemic: La Caduta di Roma
  - 2. «mi piacerebbe che si giocasse tutti insieme contro il gio…» → None: no games
- **deckbuilding-meccanica** — converged turn 2, cost 6 LLM calls / 7404 tok
  - 1. «cerco un gioco per il mio gruppo, siamo in tre o quattro …» → None FALLBACK: Through the Ages, Altiplano di Giochix, Puerto Rico
  - 2. «in particolare adoriamo i giochi dove costruisci e potenz…» → None: Clank!, Pot de Vin
- **gestionale-worker-placement** — converged turn 2, cost 6 LLM calls / 6477 tok
  - 1. «siamo giocatori esperti e vogliamo un gestionale impegnat…» → None: Talisman: Il Cataclisma
  - 2. «ci piace soprattutto piazzare i lavoratori per raccoglier…» → None: Agricola, Puerto Rico
- **regalo-bambino-8anni** — converged turn 2, cost 6 LLM calls / 7113 tok
  - 1. «devo fare un regalo a un bambino di 8 anni, non gioca anc…» → None: Agricola, Pandemic: La Caduta di Roma
  - 2. «qualcosa di semplice e colorato, con regole che si spiega…» → None FALLBACK: Fantascatti Special, 5 Minute Chase, Fairy Tile
- **horror-cooperativo** — converged turn 1, cost 4 LLM calls / 4544 tok
  - 1. «vorremmo un gioco cooperativo per una serata a tema horro…» → None: Fireteam Zero, Le Case della Follia
  - 2. «ci piace esplorare posti inquietanti e affrontare l'orror…» → None: no games

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
