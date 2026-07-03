<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — ChatRetrieve — _retrieve

> recall@k **0.818** · 11 cases (mean rank of found: 1.78) · embeddings `bge-m3` · session 20260703-132824

```
  Cases: 11   recall@k: 0.818 ↓ (Δ -0.182, was: 1.000)
  Found: 9/11   mean rank of found: 1.78 (was: 1.73)

  ✓ onitama-due-veloce-astratto            rank  2 / k=4
  ✓ terraforming-engine-spazio             rank  3 / k=5
  ✓ carcassonne-tessere-in-due             rank  1 / k=4
  ✗ pandemic-regalo-cooperativo            rank  — / k=2
  ✗ bang-serata-tanti-amici                rank  — / k=4
  ✓ agricola-fattoria-in-due               rank  1 / k=4
  ✓ star-wars-legion-miniature             rank  1 / k=5
  ✓ king-of-tokyo-dadi-mostri              rank  2 / k=4
  ✓ trono-di-spade-intrighi                rank  4 / k=5
  ✓ ticket-to-ride-treni-genitori          rank  1 / k=2
  ✓ dead-mans-doubloons-click-pirati       rank  1 / k=4
```

## Failures (2)

### pandemic-regalo-cooperativo
- expected_id: `3`
- k_used: `2`
- conversation:
  - utente: cerco un regalo per mia sorella, gioca spesso a giochi da tavolo con i figli di 8 e 11 anni
  - bot: Che bel regalo! Che genere di giochi piacciono in famiglia? Più strategia o più divertimento veloce?
- message: preferirei un gioco collaborativo, dove si vince o si perde tutti insieme, così i bambini non litigano
- top_hits:
  - id=50, name='Solenia - Gioco da Tavolo Strategico per Famiglie | Esplora Luce e Ombra | 2-4 Giocatori, 10 Anni, 45 Minuti, Asmodee'
  - id=11, name='Fireteam Zero - Gioco da Tavolo Horror Cooperativo per 1-4 Giocatori, Dungeon Crawler e Combattimento Strategico, 90 Minuti di A'
- note: GUIDED puts only 2 games on the table. The corpus has six cooperatives; the family-with-kids context lives ONLY in turn 1, the coop request only in turn 3 — the assembly must combine them to beat the 14+ horror coops.

### bang-serata-tanti-amici
- expected_id: `51`
- k_used: `4`
- conversation:
  - utente: sabato organizzo una serata a casa, saremo in sette o otto amici e vogliamo soprattutto ridere
  - bot: Perfetto! Per i gruppi numerosi ci sono party game e giochi di carte molto divertenti. Che stile preferite?
- message: boh, scegli tu, basta che faccia divertire tutti
- top_hits:
  - id=44, name='Overseers - Gioco di Carte Strategico per 3-6 Giocatori, Bluff e Drafting, Divertimento per Tutti, Età 14+ - Gate On Games'
  - id=41, name='Dixit - Gioco di Carte di Fantasia e Intuizione per 4-8 Giocatori, Divertimento Familiare in 30 Minuti - Asmodee'
  - id=40, name='Ticket to Ride: Europa'
  - id=13, name='Ticket to Ride: Vagoni & Velieri'
- note: The current message ALONE is useless ('scegli tu'): player count (7-8) and mood (laughing) live entirely in turn 1. A single-message test could never pass this; it isolates the history contribution to the query.

## Passes (9)

- **onitama-due-veloce-astratto** — rank 2
- **terraforming-engine-spazio** — rank 3
- **carcassonne-tessere-in-due** — rank 1
- **agricola-fattoria-in-due** — rank 1
- **star-wars-legion-miniature** — rank 1
- **king-of-tokyo-dadi-mostri** — rank 2
- **trono-di-spade-intrighi** — rank 4
- **ticket-to-ride-treni-genitori** — rank 1
- **dead-mans-doubloons-click-pirati** — rank 1

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
