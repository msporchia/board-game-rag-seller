<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — ChatRetrieve — _retrieve

> recall@k **0.545** · 11 cases (mean rank of found: 1.33) · embeddings `nomic-embed-text` · session 20260611-123159

```
  Cases: 11   recall@k: 0.545 ↑ (Δ +0.182, was: 0.364)
  Found: 6/11   mean rank of found: 1.33 (was: 1.0)

  ✓ onitama-due-veloce-astratto            rank  2 / k=4
  ✓ terraforming-engine-spazio             rank  1 / k=5
  ✓ carcassonne-tessere-in-due             rank  1 / k=4
  ✓ pandemic-regalo-cooperativo            rank  2 / k=2
  ✗ bang-serata-tanti-amici                rank  — / k=4
  ✗ agricola-fattoria-in-due               rank  — / k=4
  ✓ star-wars-legion-miniature             rank  1 / k=5
  ✓ king-of-tokyo-dadi-mostri              rank  1 / k=4
  ✗ trono-di-spade-intrighi                rank  — / k=5
  ✗ ticket-to-ride-treni-genitori          rank  — / k=2
  ✗ dead-mans-doubloons-click-pirati       rank  — / k=4
```

## Failures (5)

### bang-serata-tanti-amici
- expected_id: `51`
- k_used: `4`
- conversation:
  - utente: sabato organizzo una serata a casa, saremo in sette o otto amici e vogliamo soprattutto ridere
  - bot: Perfetto! Per i gruppi numerosi ci sono party game e giochi di carte molto divertenti. Che stile preferite?
- message: boh, scegli tu, basta che faccia divertire tutti
- top_hits:
  - id=37, name='Fantascatti Special - Gioco di Destrezza e Abilità per 4-8 Giocatori con Cappello Magico - Divertimento in Famiglia!'
  - id=6, name='Star Wars: Legion - Gioco di Miniature Strategico per 2 Giocatori, 33 Miniature, Battaglie Epiche, 120 Min, Alex Davy, Asmodee'
  - id=56, name='Fairy Tile - Gioco da Tavolo di Piazzamento Tessere per Famiglie, Avventure Fantasiose per 2-4 Giocatori, Età 8+'
  - id=42, name='Citadels - Gioco di Strategia Medievale, 2-7 Giocatori, 60 Minuti di Divertimento, Autore Bruno Faidutti, Asmodee'
- note: The current message ALONE is useless ('scegli tu'): player count (7-8) and mood (laughing) live entirely in turn 1. A single-message test could never pass this; it isolates the history contribution to the query.

### agricola-fattoria-in-due
- expected_id: `29`
- k_used: `4`
- conversation:
  - utente: a me e alla mia ragazza piacciono i gestionali a tema campagna
  - bot: Bella scelta! Vi piace di più coltivare i campi, allevare animali o commerciare i raccolti?
- message: qualcosa dove mandi avanti una fattoria, con gli animali e i campi da coltivare
- choices:
  - per 2 giocatori
- top_hits:
  - id=6, name='Star Wars: Legion - Gioco di Miniature Strategico per 2 Giocatori, 33 Miniature, Battaglie Epiche, 120 Min, Alex Davy, Asmodee'
  - id=34, name='Carcassonne - Nuova Edizione | Gioco Strategico per Famiglia, 2-5 Giocatori, 45 Minuti di Divertimento - Giochi Uniti'
  - id=50, name='Solenia - Gioco da Tavolo Strategico per Famiglie | Esplora Luce e Ombra | 2-4 Giocatori, 10 Anni, 45 Minuti, Asmodee'
  - id=160, name='Onitama - Gioco Strategico di Arti Marziali per 2 Giocatori, 10 Minuti di Sfida, Design Elegante e Regole Semplici'
- note: The click 'per 2 giocatori' becomes a hard players filter. Viticulture (vineyard) and Stone Age are the farming-flavored confounders that survive the filter; the query must pick the farm-with-animals one.

### trono-di-spade-intrighi
- expected_id: `31`
- k_used: `5`
- conversation:
  - utente: siamo un gruppo di giocatori navigati, le partite lunghe e pesanti non ci spaventano
  - bot: Ottimo, allora possiamo puntare sui titoli più impegnativi del catalogo. Che ambientazione vi attira?
- message: fantasy, ma con tanta politica: alleanze, tradimenti e guerre tra grandi casate
- top_hits:
  - id=56, name='Fairy Tile - Gioco da Tavolo di Piazzamento Tessere per Famiglie, Avventure Fantasiose per 2-4 Giocatori, Età 8+'
  - id=8, name='Dungeon Saga: La Missione del Re dei Nani - Gioco da Tavolo Fantasy per 2-5 Giocatori, Avventure e Combattimenti in Italiano'
  - id=6, name='Star Wars: Legion - Gioco di Miniature Strategico per 2 Giocatori, 33 Miniature, Battaglie Epiche, 120 Min, Alex Davy, Asmodee'
  - id=10, name='First Martians - Avventure sul Pianeta Rosso | Gioco Cooperativo 1-4 Giocatori | Sfide di Sopravvivenza Spaziale e Strategia'
  - id=1, name='Massive Darkness - Gioco Cooperativo Fantasy con Miniature | 1-6 Giocatori | Dungeon Crawler Avventura - Italiano Asmodee'
- note: Experienced big-group context (turn 1) + political fantasy warfare (turn 3). Schönbrunn (diplomacy) and Overseers (bluff) are the politics confounders; null k exercises the DISCOVERY default of 5.

### ticket-to-ride-treni-genitori
- expected_id: `40`
- k_used: `2`
- conversation:
  - utente: mi serve un gioco da fare quando vengono a trovarci i miei genitori, niente di complicato
  - bot: Capisco, meglio un gioco con regole semplici e immediate. C'è un tema che potrebbe piacere a tutti?
- message: a mio padre piacciono i treni e i viaggi
- top_hits:
  - id=52, name="8Bit Box - Gioco da Tavolo Nostalgico per 3-6 Giocatori, Rivivi i Videogiochi degli Anni '80 con 3 Iconici Giochi!"
  - id=55, name='Kanagawa - Gioco da Tavolo Artistico per 2-4 Giocatori, Ispirato a Hokusai, 45 Minuti di Creatività e Strategia, Complessità M'
- note: GUIDED k=2 with two trains games in the corpus: Ticket to Ride Europa (45 min, simple — fits 'niente di complicato' from turn 1) vs Vagoni & Velieri (90 min). The simplicity cue lives only in the earlier turn.

### dead-mans-doubloons-click-pirati
- expected_id: `46`
- k_used: `4`
- conversation:
  - utente: vorrei regalare qualcosa di avventuroso a un amico
  - bot: Abbiamo tanti giochi d'avventura! Ti attira più l'esplorazione, il combattimento o un tema particolare?
- message: vediamo un po', cosa mi consigli?
- choices:
  - a tema pirati
- top_hits:
  - id=3, name='Pandemic: 10th Anniversary - Edizione Speciale in Scatola di Metallo con Miniature e Componenti di Alta Qualità - Gioco Coopera'
  - id=40, name='Ticket to Ride: Europa'
  - id=42, name='Citadels - Gioco di Strategia Medievale, 2-7 Giocatori, 60 Minuti di Divertimento, Autore Bruno Faidutti, Asmodee'
  - id=13, name='Ticket to Ride: Vagoni & Velieri'
- note: The click 'a tema pirati' does NOT parse into a structured filter: it must survive as a query leftover. The current message carries no signal, so this isolates the leftovers path of the query assembly.

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
