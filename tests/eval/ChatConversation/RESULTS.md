<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — ChatConversation — full multi-turn sessions

> case pass **0.700** · 10 conversations / 22 turns (convergence 0.625, fallback/turn 0.045) · model `llama3.1` · session 20260612-081949

```
  Conversations: 10   turns: 22   fallback/turn: 0.045

  case_pass           7/10 0.700   [all conversations]
  convergence         5/8  0.625   [cases with an accepted-games oracle]
  turn_oracles        6/6  1.000   [declared per-turn checks]
  filters_ok          3/3  1.000   [cases with a final-filters oracle]
  proposal_ok         1/1  1.000   [cases with the forced-proposal oracle]
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
  -    [GUIDED] Specie Dominanti - Gioco da Tavolo Preistorico di Strategia per 2-6 Giocatori, 120 Minuti di Divertimento e Competizione Asmodee, La Festa per Odino: I Norvegesi - Espansione Gioco di Uwe Rosenberg, 1-4 Giocatori, Strategia e Avventura Vichinga, Cranio Creat, Specie Dominanti - Gioco da Tavolo Preistorico di Strategia per 2-6 Giocatori, 120 Minuti di Divertimento e Competizione Asmodee — bot: Ciao! Sono felice di aiutarti a trovare un nuovo gioco per il tuo gruppo di giocatori esperti. Sembra che vi piacciano i titoli impegnativi, quindi ti propongo 
  - 2. utente: il tema che ci attira di più è la fantascienza
  -    [GUIDED] Specie Dominanti - Gioco da Tavolo Preistorico di Strategia per 2-6 Giocatori, 120 Minuti di Divertimento e Competizione Asmodee, La Festa per Odino: I Norvegesi - Espansione Gioco di Uwe Rosenberg, 1-4 Giocatori, Strategia e Avventura Vichinga, Cranio Creat — bot: Fantascienza, eh? Sembra che vi piacciano i titoli impegnativi e le storie futuristiche! Specie Dominanti è un gioco di strategia preistorica che vi porterà a s
  - 3. utente: l'ideale sarebbe qualcosa dove costruisci un motore di carte e risorse per rendere abitabile un pianeta
  -    [GUIDED] Specie Dominanti - Gioco da Tavolo Preistorico di Strategia per 2-6 Giocatori, 120 Minuti di Divertimento e Competizione Asmodee, Specie Dominanti - Gioco da Tavolo Preistorico di Strategia per 2-6 Giocatori, 120 Minuti di Divertimento e Competizione Asmodee — bot: Fantascienza, eh? Sembra che vi piacciano i titoli impegnativi e le storie futuristiche! Ho capito che cercate qualcosa dove costruire un motore di carte e riso
- expected: accept_ids=[21], by_turn=3
- note: Vague-to-specific convergence: heavy-gamer context (turn 1), sci-fi theme (turn 2), engine-building on a planet (turn 3). Terraforming Mars must surface by turn 3; Progetto Gaia, First Martians and Mercanti di Venere are the in-corpus sci-fi confounders.

### contrordine-giocatori
- failed:
  - convergence (by turn 2)
- trajectory:
  - 1. utente: cerco un gioco collaborativo da fare con i miei figli di 8 anni + click ['per 4 giocatori']
  -    [QUICK_MATCH] Fairy Tile - Gioco da Tavolo di Piazzamento Tessere per Famiglie, Avventure Fantasiose per 2-4 Giocatori, Età 8+, 8Bit Box - Gioco da Tavolo Nostalgico per 3-6 Giocatori, Rivivi i Videogiochi degli Anni '80 con 3 Iconici Giochi!, Dixit - Gioco di Carte di Fantasia e Intuizione per 4-8 Giocatori, Divertimento Familiare in 30 Minuti - Asmodee — bot: Ciao! Sono felice di aiutarti a trovare un gioco collaborativo perfetto per te e i tuoi figli di 8 anni. Ecco alcune opzioni che potrebbero piacere! Fairy Tile 
  - 2. utente: anzi, ripensandoci i grandi non giocano quasi mai: meglio qualcosa che funzioni bene in due + click ['per 2 giocatori']
  -    [GUIDED] Fairy Tile - Gioco da Tavolo di Piazzamento Tessere per Famiglie, Avventure Fantasiose per 2-4 Giocatori, Età 8+, Massive Darkness - Gioco Cooperativo Fantasy con Miniature | 1-6 Giocatori | Dungeon Crawler Avventura - Italiano Asmodee — bot: Ciao! Sembra che i tuoi figli siano grandi abbastanza per giocare con te, ma non sempre partecipano alle sessioni di gioco. Vorrei suggerirti due giochi che pot
- expected: accept_ids=[3, 48], by_turn=2, filters={'players': {'vals': [2]}}
- final_filters: players={'vals': [2]}
- note: Constraint reversal: the turn-2 click must REPLACE the players filter (latest wins), not pile up — final filters_spec must say players=[2]. Family coop for an 8-year-old: both Pandemics (age 8, coop, 2 players ok); the age-14 horror coops are the confounders.

### pandemic-famiglia-cooperativo
- failed:
  - convergence (by turn 2)
- trajectory:
  - 1. utente: vorrei un gioco da fare con tutta la famiglia, i bambini hanno 8 anni
  -    [QUICK_MATCH] Fantascatti Special - Gioco di Destrezza e Abilità per 4-8 Giocatori con Cappello Magico - Divertimento in Famiglia!, Fairy Tile - Gioco da Tavolo di Piazzamento Tessere per Famiglie, Avventure Fantasiose per 2-4 Giocatori, Età 8+, Dixit - Gioco di Carte di Fantasia e Intuizione per 4-8 Giocatori, Divertimento Familiare in 30 Minuti - Asmodee — bot: Ciao! Sono felice di aiutarti a trovare un gioco divertente per tutta la famiglia! Fantascatti Special è il perfetto gioco di destrezza e abilità per i bambini 
  - 2. utente: mi piacerebbe che si giocasse tutti insieme contro il gioco, senza vincitori e vinti, così non litigano
  -    [QUICK_MATCH] Fairy Tile - Gioco da Tavolo di Piazzamento Tessere per Famiglie, Avventure Fantasiose per 2-4 Giocatori, Età 8+, Solenia - Gioco da Tavolo Strategico per Famiglie | Esplora Luce e Ombra | 2-4 Giocatori, 10 Anni, 45 Minuti, Asmodee, Fantascatti Special - Gioco di Destrezza e Abilità per 4-8 Giocatori con Cappello Magico - Divertimento in Famiglia! — bot: Fantastico! Sembra che stiate cercando un gioco da tavolo per tutta la famiglia, senza vincitori e vinti. Ho alcune ottime proposte per voi! Fairy Tile è un gio
- expected: accept_ids=[3, 48], by_turn=2
- note: Constraints split across turns, no clicks: family-with-8-year-olds lives only in turn 1, the coop request only in turn 2. The query assembly must combine them to beat the six age-14 horror coops; both Pandemics are accepted.

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
