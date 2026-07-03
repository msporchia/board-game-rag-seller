<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — GameRetriever — search() vs ordered oracle

> mean NDCG **0.726** · 12 cases (2 perfect, 6 ≥0.8) · embeddings `bge-m3` · session 20260703-132817

```
  Cases: 12   mean NDCG: 0.726 ↑ (Δ +0.025, was: 0.701)
  Perfect: 2/12   close (≥0.8): 6/12   mean displacement: 2.82 (was: 3.51)

  ✗ coop-famiglia-figli                ndcg 0.000   oracle ranks: #16 #7 #4
  ✗ astratto-due-veloce                ndcg 0.397   oracle ranks: #2 #7 #24
  ✗ serata-tanti-amici                 ndcg 0.553   oracle ranks: #7 #1 #2
  ✗ deck-building-dungeon              ndcg 0.630   oracle ranks: #1 #6 #9
  ✗ wargame-scifi-due-miniature        ndcg 0.760   oracle ranks: #1 #11
  ✗ pirati-navi-tesori                 ndcg 0.760   oracle ranks: #1 #6
  ✓ spazio-gestionale-impegnativo      ndcg 0.817   oracle ranks: #2 #1 #4
  ✓ fattoria-piazzamento-lavoratori    ndcg 0.895   oracle ranks: #1 #2 #12
  ✓ tessere-medioevo-famiglia          ndcg 0.922   oracle ranks: #2 #1 #3
  ✓ horror-cooperativo-indagine        ndcg 0.973   oracle ranks: #1 #3 #2
  ✓ mitologia-greca                    ndcg 1.000   oracle ranks: #1 #2
  ✓ treni-famiglia-percorsi            ndcg 1.000   oracle ranks: #1 #2
```

## Failures (6)

### coop-famiglia-figli
- ndcg: `0.0`
- mean_displacement: `7.0`
- query: Vorrei un gioco cooperativo da fare con i miei figli, niente di troppo lungo o complicato
- oracle:
  - id=3, name='Pandemic: 10th Anniversary - Edizione Speciale in Scatola di Metallo con Miniature e Componenti di Alta Qualità - Gioco Coopera', expected_pos=1, rank=16
  - id=48, name='Pandemic: La Caduta di Roma - Gioco Cooperativo per 1-5 Giocatori, Strategia ed Azione Epica, 60 Minuti di Divertimento', expected_pos=2, rank=7
  - id=1, name='Massive Darkness - Gioco Cooperativo Fantasy con Miniature | 1-6 Giocatori | Dungeon Crawler Avventura - Italiano Asmodee', expected_pos=3, rank=4
- window:
  - id=41, name='Dixit - Gioco di Carte di Fantasia e Intuizione per 4-8 Giocatori, Divertimento Familiare in 30 Minuti - Asmodee'
  - id=56, name='Fairy Tile - Gioco da Tavolo di Piazzamento Tessere per Famiglie, Avventure Fantasiose per 2-4 Giocatori, Età 8+'
  - id=40, name='Ticket to Ride: Europa'
  - id=1, name='Massive Darkness - Gioco Cooperativo Fantasy con Miniature | 1-6 Giocatori | Dungeon Crawler Avventura - Italiano Asmodee'
  - id=27, name='Clank! - Gioco di Deck-Building Avventuroso per 2-4 Giocatori, Esplora la Fortezza del Drago, Voto GameNest 7.8, Italiano'
- note: Six cooperatives in the corpus; the family constraint orders them: Pandemic (45min, medium-light) > Pandemic La Caduta di Roma (60min, medium) > Massive Darkness (coop but a 120min dungeon crawler). The horror coops (Case della Follia, Fireteam Zero) and the heavy First Martians must stay below the oracle.

### astratto-due-veloce
- ndcg: `0.3975`
- mean_displacement: `9.0`
- query: Un gioco astratto veloce per due, tipo scacchi ma che duri dieci minuti
- oracle:
  - id=160, name='Onitama - Gioco Strategico di Arti Marziali per 2 Giocatori, 10 Minuti di Sfida, Design Elegante e Regole Semplici', expected_pos=1, rank=2
  - id=47, name='Tao Long: Gioco da Tavolo Strategico per 2 Giocatori - Duello di Dragoni e Movimento del Bagua - Durata 20 Minuti - Gate On Game', expected_pos=2, rank=7
  - id=43, name='Spirits of the Forest - Gioco di Strategia per Famiglia | 1-4 Giocatori | Card Drafting | Divertente e Veloce (20 Min)', expected_pos=3, rank=24
- window:
  - id=32, name='5 Minute Chase - Gioco di Fuga Asimmetrico per 2-4 Giocatori, Azione in Tempo Reale, Divertimento Familiare, 15 Minuti di Gioco'
  - id=160, name='Onitama - Gioco Strategico di Arti Marziali per 2 Giocatori, 10 Minuti di Sfida, Design Elegante e Regole Semplici'
  - id=19, name='Near and Far - Gioco da Tavolo di Avventura per 2-4 Giocatori, di Ryan Laukat - Durata 120 min - Esplora Mondi Perduti!'
  - id=41, name='Dixit - Gioco di Carte di Fantasia e Intuizione per 4-8 Giocatori, Divertimento Familiare in 30 Minuti - Asmodee'
  - id=20, name='Stone Age: 10° Anniversario - Edizione Limitata | Gioco da Tavolo Strategico 2-4 Giocatori, 90 Minuti - Giochi Uniti'
- note: Onitama is exact (2p, 10min, chess-like abstract) > Tao Long (2p, 20min abstract duel) > Spirits of the Forest (light abstract, but 1-4p and not a duel).

### serata-tanti-amici
- ndcg: `0.5525`
- mean_displacement: `2.67`
- query: Stasera siamo tanti, anche sette o otto, serve qualcosa di semplice che faccia ridere
- oracle:
  - id=51, name='BANG! Deluxe - Gioco di Carte Strategico per 3-8 Giocatori, Avventura nel Selvaggio West, Divertimento da 30 Minuti!', expected_pos=1, rank=7
  - id=37, name='Fantascatti Special - Gioco di Destrezza e Abilità per 4-8 Giocatori con Cappello Magico - Divertimento in Famiglia!', expected_pos=2, rank=1
  - id=41, name='Dixit - Gioco di Carte di Fantasia e Intuizione per 4-8 Giocatori, Divertimento Familiare in 30 Minuti - Asmodee', expected_pos=3, rank=2
- window:
  - id=37, name='Fantascatti Special - Gioco di Destrezza e Abilità per 4-8 Giocatori con Cappello Magico - Divertimento in Famiglia!'
  - id=41, name='Dixit - Gioco di Carte di Fantasia e Intuizione per 4-8 Giocatori, Divertimento Familiare in 30 Minuti - Asmodee'
  - id=40, name='Ticket to Ride: Europa'
  - id=52, name="8Bit Box - Gioco da Tavolo Nostalgico per 3-6 Giocatori, Rivivi i Videogiochi degli Anni '80 con 3 Iconici Giochi!"
  - id=13, name='Ticket to Ride: Vagoni & Velieri'
- note: BANG! Deluxe (3-8p, bluff, humor) > Fantascatti (2-8p, frantic dexterity party) > Dixit (party humor but caps at fewer players). King of Tokyo near Dixit is a near-miss (fun but caps at 6).

### deck-building-dungeon
- ndcg: `0.63`
- mean_displacement: `3.33`
- query: Un deck building d'avventura, esplorare un sotterraneo e arraffare tesori prima degli altri
- oracle:
  - id=27, name='Clank! - Gioco di Deck-Building Avventuroso per 2-4 Giocatori, Esplora la Fortezza del Drago, Voto GameNest 7.8, Italiano', expected_pos=1, rank=1
  - id=18, name='Altiplano di Giochix - Gioco di Strategia per 2-5 Giocatori, 120 Minuti di Avventure e Sfide in Alta Quota, Ideato da Reiner Sto', expected_pos=2, rank=6
  - id=33, name='Newton - Gioco da Tavolo Strategico per 2-4 Giocatori | Avventura nel Diciottesimo Secolo | Deckbuilding e Gestione della Mano', expected_pos=3, rank=9
- window:
  - id=27, name='Clank! - Gioco di Deck-Building Avventuroso per 2-4 Giocatori, Esplora la Fortezza del Drago, Voto GameNest 7.8, Italiano'
  - id=21, name='Terraforming Mars'
  - id=19, name='Near and Far - Gioco da Tavolo di Avventura per 2-4 Giocatori, di Ryan Laukat - Durata 120 min - Esplora Mondi Perduti!'
  - id=10, name='First Martians - Avventure sul Pianeta Rosso | Gioco Cooperativo 1-4 Giocatori | Sfide di Sopravvivenza Spaziale e Strategia'
  - id=56, name='Fairy Tile - Gioco da Tavolo di Piazzamento Tessere per Famiglie, Avventure Fantasiose per 2-4 Giocatori, Età 8+'
- note: Clank! is the literal answer (deck building + dungeon delve + treasure race) > Altiplano (bag building economy, no dungeon) > Newton (deck/pool building, scientific travel). The order of the last two is mechanical-affinity grading, a swap there is a minor deviation.

### wargame-scifi-due-miniature
- ndcg: `0.7602`
- mean_displacement: `4.5`
- query: Un wargame di fantascienza con le miniature, per giocare in due
- oracle:
  - id=6, name='Star Wars: Legion - Gioco di Miniature Strategico per 2 Giocatori, 33 Miniature, Battaglie Epiche, 120 Min, Alex Davy, Asmodee', expected_pos=1, rank=1
  - id=16, name='Warhammer 40,000: Heroes of Black Reach - Gioco da Tavolo Strategico per 2 Giocatori, 90 Minuti di Battaglie Epiche in Italiano', expected_pos=2, rank=11
- window:
  - id=6, name='Star Wars: Legion - Gioco di Miniature Strategico per 2 Giocatori, 33 Miniature, Battaglie Epiche, 120 Min, Alex Davy, Asmodee'
  - id=1, name='Massive Darkness - Gioco Cooperativo Fantasy con Miniature | 1-6 Giocatori | Dungeon Crawler Avventura - Italiano Asmodee'
  - id=160, name='Onitama - Gioco Strategico di Arti Marziali per 2 Giocatori, 10 Minuti di Sfida, Design Elegante e Regole Semplici'
  - id=56, name='Fairy Tile - Gioco da Tavolo di Piazzamento Tessere per Famiglie, Avventure Fantasiose per 2-4 Giocatori, Età 8+'
- note: Star Wars Legion (2p sci-fi miniatures wargame, explicit miniatures) > Warhammer 40k Heroes of Black Reach (2p sci-fi wargame, counters/dice). Both fit; Legion is the stronger miniatures match.

### pirati-navi-tesori
- ndcg: `0.7602`
- mean_displacement: `2.0`
- query: Un gioco di pirati, con le navi e la caccia al tesoro
- oracle:
  - id=46, name="Dead Man's Doubloons - Gioco di Avventura Pirata per 2-6 Giocatori, Combattimento e Strategia, 45 Minuti, Jason Miceli", expected_pos=1, rank=1
  - id=13, name='Ticket to Ride: Vagoni & Velieri', expected_pos=2, rank=6
- window:
  - id=46, name="Dead Man's Doubloons - Gioco di Avventura Pirata per 2-6 Giocatori, Combattimento e Strategia, 45 Minuti, Jason Miceli"
  - id=36, name='Puerto Rico - Gioco da Tavolo Strategico per 2-5 Giocatori, Coltivazione ed Economia, Voto GameNest 8, 90 Minuti di Divertimento'
  - id=19, name='Near and Far - Gioco da Tavolo di Avventura per 2-4 Giocatori, di Ryan Laukat - Durata 120 min - Esplora Mondi Perduti!'
  - id=27, name='Clank! - Gioco di Deck-Building Avventuroso per 2-4 Giocatori, Esplora la Fortezza del Drago, Voto GameNest 7.8, Italiano'
- note: Dead Man's Doubloons is the only pirate game (ships, treasure race) > Ticket to Ride Vagoni & Velieri (the only other ships game, graded relevance only).

## Passes (6)

- **spazio-gestionale-impegnativo** — ndcg 0.8175
- **fattoria-piazzamento-lavoratori** — ndcg 0.895
- **tessere-medioevo-famiglia** — ndcg 0.9225
- **horror-cooperativo-indagine** — ndcg 0.9725
- **mitologia-greca** — ndcg 1.0
- **treni-famiglia-percorsi** — ndcg 1.0

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
