<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — GameRetriever — search() vs ordered oracle

> mean NDCG **0.386** · 12 cases (0 perfect, 1 ≥0.8) · embeddings `nomic-embed-text` · session 20260611-123014

```
  Cases: 12   mean NDCG: 0.386 → (Δ +0.000, was: 0.386)
  Perfect: 0/12   close (≥0.8): 1/12   mean displacement: 10.68 (was: 10.68)

  ✗ mitologia-greca                    ndcg 0.000   oracle ranks: #12 #26
  ✗ treni-famiglia-percorsi            ndcg 0.000   oracle ranks: #3 #22
  ✗ tessere-medioevo-famiglia          ndcg 0.000   oracle ranks: #4 #33 #12
  ✗ coop-famiglia-figli                ndcg 0.132   oracle ranks: #6 #5 #2
  ✗ spazio-gestionale-impegnativo      ndcg 0.210   oracle ranks: #37 #3 #45
  ✗ serata-tanti-amici                 ndcg 0.210   oracle ranks: #17 #3 #35
  ✗ astratto-due-veloce                ndcg 0.420   oracle ranks: #8 #1 #17
  ✗ pirati-navi-tesori                 ndcg 0.480   oracle ranks: #2 #7
  ✗ fattoria-piazzamento-lavoratori    ndcg 0.735   oracle ranks: #3 #1 #26
  ✗ wargame-scifi-due-miniature        ndcg 0.760   oracle ranks: #1 #22
  ✗ deck-building-dungeon              ndcg 0.763   oracle ranks: #1 #31 #2
  ✓ horror-cooperativo-indagine        ndcg 0.922   oracle ranks: #2 #1 #3
```

## Failures (11)

### mitologia-greca
- ndcg: `0.0`
- mean_displacement: `17.5`
- query: Qualcosa ambientato nella mitologia greca, con gli dèi dell'Olimpo
- oracle:
  - id=2, name="Lords of Hellas - Gioco da Tavolo Strategico di Mitologia Greca per 1-4 Giocatori, 120 Minuti d'Avventura, Adam Kwapinski", expected_pos=1, rank=12
  - id=49, name='Orbis - Gioco di Piazzamento Tessere per 2-4 Giocatori, Strategia e Creatività, Diventa una Divinità! (45 Min) - Space Cowboys', expected_pos=2, rank=26
- window:
  - id=4, name="Le Case della Follia - Seconda Edizione | Gioco da Tavolo Horror Cooperativo | Esplora Arkham e Affronta l'Orrore"
  - id=30, name='Amun-Re - Gioco di Strategia Antico Egitto di Reiner Knizia, Aste e Controllo Territorio, 3-5 Giocatori, 90 Minuti - Dv Giochi'
  - id=48, name='Pandemic: La Caduta di Roma - Gioco Cooperativo per 1-5 Giocatori, Strategia ed Azione Epica, 60 Minuti di Divertimento'
  - id=18, name='Altiplano di Giochix - Gioco di Strategia per 2-5 Giocatori, 120 Minuti di Avventure e Sfide in Alta Quota, Ideato da Reiner Sto'
- note: Lords of Hellas is explicit Greek mythology (Zeus, Athena, monuments) > Orbis (generic god-and-creation mythology). Amun-Re is Egyptian: above Orbis would be a near-miss, above Hellas a real error.

### treni-famiglia-percorsi
- ndcg: `0.0`
- mean_displacement: `11.0`
- query: Un gioco di treni per la famiglia, dove si costruiscono i percorsi sulla mappa
- oracle:
  - id=40, name='Ticket to Ride: Europa', expected_pos=1, rank=3
  - id=13, name='Ticket to Ride: Vagoni & Velieri', expected_pos=2, rank=22
- window:
  - id=34, name='Carcassonne - Nuova Edizione | Gioco Strategico per Famiglia, 2-5 Giocatori, 45 Minuti di Divertimento - Giochi Uniti'
  - id=45, name='Pot de Vin - Gioco di Carte Strategico per 3-6 Giocatori, Divertimento Tardo Medievale, Collezione e Inganno, 30 Minuti'
  - id=40, name='Ticket to Ride: Europa'
  - id=55, name='Kanagawa - Gioco da Tavolo Artistico per 2-4 Giocatori, Ispirato a Hokusai, 45 Minuti di Creatività e Strategia, Complessità M'
- note: Two train games in the corpus: Ticket to Ride Europa is the pure-trains classic asked for > Vagoni & Velieri (the trains-plus-ships variant).

### tessere-medioevo-famiglia
- ndcg: `0.0`
- mean_displacement: `14.33`
- query: Un gioco di piazzamento tessere ambientato nel medioevo, semplice, per la famiglia
- oracle:
  - id=34, name='Carcassonne - Nuova Edizione | Gioco Strategico per Famiglia, 2-5 Giocatori, 45 Minuti di Divertimento - Giochi Uniti', expected_pos=1, rank=4
  - id=56, name='Fairy Tile - Gioco da Tavolo di Piazzamento Tessere per Famiglie, Avventure Fantasiose per 2-4 Giocatori, Età 8+', expected_pos=2, rank=33
  - id=49, name='Orbis - Gioco di Piazzamento Tessere per 2-4 Giocatori, Strategia e Creatività, Diventa una Divinità! (45 Min) - Space Cowboys', expected_pos=3, rank=12
- window:
  - id=50, name='Solenia - Gioco da Tavolo Strategico per Famiglie | Esplora Luce e Ombra | 2-4 Giocatori, 10 Anni, 45 Minuti, Asmodee'
  - id=30, name='Amun-Re - Gioco di Strategia Antico Egitto di Reiner Knizia, Aste e Controllo Territorio, 3-5 Giocatori, 90 Minuti - Dv Giochi'
  - id=43, name='Spirits of the Forest - Gioco di Strategia per Famiglia | 1-4 Giocatori | Card Drafting | Divertente e Veloce (20 Min)'
  - id=34, name='Carcassonne - Nuova Edizione | Gioco Strategico per Famiglia, 2-5 Giocatori, 45 Minuti di Divertimento - Giochi Uniti'
  - id=40, name='Ticket to Ride: Europa'
- note: Carcassonne is exact (medieval tile placement, family weight) > Fairy Tile (family tile placement, fairy-tale medieval) > Orbis (tile placement, but mythology and more thinky).

### coop-famiglia-figli
- ndcg: `0.1325`
- mean_displacement: `3.0`
- query: Vorrei un gioco cooperativo da fare con i miei figli, niente di troppo lungo o complicato
- oracle:
  - id=3, name='Pandemic: 10th Anniversary - Edizione Speciale in Scatola di Metallo con Miniature e Componenti di Alta Qualità - Gioco Coopera', expected_pos=1, rank=6
  - id=48, name='Pandemic: La Caduta di Roma - Gioco Cooperativo per 1-5 Giocatori, Strategia ed Azione Epica, 60 Minuti di Divertimento', expected_pos=2, rank=5
  - id=1, name='Massive Darkness - Gioco Cooperativo Fantasy con Miniature | 1-6 Giocatori | Dungeon Crawler Avventura - Italiano Asmodee', expected_pos=3, rank=2
- window:
  - id=10, name='First Martians - Avventure sul Pianeta Rosso | Gioco Cooperativo 1-4 Giocatori | Sfide di Sopravvivenza Spaziale e Strategia'
  - id=1, name='Massive Darkness - Gioco Cooperativo Fantasy con Miniature | 1-6 Giocatori | Dungeon Crawler Avventura - Italiano Asmodee'
  - id=56, name='Fairy Tile - Gioco da Tavolo di Piazzamento Tessere per Famiglie, Avventure Fantasiose per 2-4 Giocatori, Età 8+'
  - id=160, name='Onitama - Gioco Strategico di Arti Marziali per 2 Giocatori, 10 Minuti di Sfida, Design Elegante e Regole Semplici'
  - id=48, name='Pandemic: La Caduta di Roma - Gioco Cooperativo per 1-5 Giocatori, Strategia ed Azione Epica, 60 Minuti di Divertimento'
- note: Six cooperatives in the corpus; the family constraint orders them: Pandemic (45min, medium-light) > Pandemic La Caduta di Roma (60min, medium) > Massive Darkness (coop but a 120min dungeon crawler). The horror coops (Case della Follia, Fireteam Zero) and the heavy First Martians must stay below the oracle.

### spazio-gestionale-impegnativo
- ndcg: `0.21`
- mean_displacement: `26.33`
- query: Un gestionale impegnativo di colonizzazione spaziale, qualcosa che faccia pensare
- oracle:
  - id=12, name='Progetto Gaia - Gioco da Tavolo Strategico di Espansione Spaziale per 1-4 Giocatori, Ispirato a Terra Mystica, Voto GameNest 8.6', expected_pos=1, rank=37
  - id=21, name='Terraforming Mars', expected_pos=2, rank=3
  - id=9, name='Mercanti di Venere - Gioco da Tavolo Strategico per 2-4 Giocatori, Avventura Spaziale, 120 Minuti, Richard Hamblen, Asmodee', expected_pos=3, rank=45
- window:
  - id=30, name='Amun-Re - Gioco di Strategia Antico Egitto di Reiner Knizia, Aste e Controllo Territorio, 3-5 Giocatori, 90 Minuti - Dv Giochi'
  - id=20, name='Stone Age: 10° Anniversario - Edizione Limitata | Gioco da Tavolo Strategico 2-4 Giocatori, 90 Minuti - Giochi Uniti'
  - id=21, name='Terraforming Mars'
  - id=34, name='Carcassonne - Nuova Edizione | Gioco Strategico per Famiglia, 2-5 Giocatori, 45 Minuti di Divertimento - Giochi Uniti'
  - id=38, name='Schönbrunn - Gioco da Tavolo Strategico di Trattative Diplomatiche (3-6 Giocatori) - Storia e Politica del XIX Secolo'
- note: Progetto Gaia (medium-heavy, space civ) > Terraforming Mars (medium, space terraforming/industry) > Mercanti di Venere (space economy, but pick-up-and-deliver adventure). First Martians just below would be acceptable (space survival coop, not a 'gestionale').

### serata-tanti-amici
- ndcg: `0.21`
- mean_displacement: `16.33`
- query: Stasera siamo tanti, anche sette o otto, serve qualcosa di semplice che faccia ridere
- oracle:
  - id=51, name='BANG! Deluxe - Gioco di Carte Strategico per 3-8 Giocatori, Avventura nel Selvaggio West, Divertimento da 30 Minuti!', expected_pos=1, rank=17
  - id=37, name='Fantascatti Special - Gioco di Destrezza e Abilità per 4-8 Giocatori con Cappello Magico - Divertimento in Famiglia!', expected_pos=2, rank=3
  - id=41, name='Dixit - Gioco di Carte di Fantasia e Intuizione per 4-8 Giocatori, Divertimento Familiare in 30 Minuti - Asmodee', expected_pos=3, rank=35
- window:
  - id=13, name='Ticket to Ride: Vagoni & Velieri'
  - id=8, name='Dungeon Saga: La Missione del Re dei Nani - Gioco da Tavolo Fantasy per 2-5 Giocatori, Avventure e Combattimenti in Italiano'
  - id=37, name='Fantascatti Special - Gioco di Destrezza e Abilità per 4-8 Giocatori con Cappello Magico - Divertimento in Famiglia!'
  - id=35, name='Talisman - Gioco da Tavolo Fantasy per 2-6 Giocatori, Avventura, Combattimenti e Magia nella Caccia alla Corona del Comando'
  - id=40, name='Ticket to Ride: Europa'
- note: BANG! Deluxe (3-8p, bluff, humor) > Fantascatti (2-8p, frantic dexterity party) > Dixit (party humor but caps at fewer players). King of Tokyo near Dixit is a near-miss (fun but caps at 6).

### astratto-due-veloce
- ndcg: `0.42`
- mean_displacement: `7.33`
- query: Un gioco astratto veloce per due, tipo scacchi ma che duri dieci minuti
- oracle:
  - id=160, name='Onitama - Gioco Strategico di Arti Marziali per 2 Giocatori, 10 Minuti di Sfida, Design Elegante e Regole Semplici', expected_pos=1, rank=8
  - id=47, name='Tao Long: Gioco da Tavolo Strategico per 2 Giocatori - Duello di Dragoni e Movimento del Bagua - Durata 20 Minuti - Gate On Game', expected_pos=2, rank=1
  - id=43, name='Spirits of the Forest - Gioco di Strategia per Famiglia | 1-4 Giocatori | Card Drafting | Divertente e Veloce (20 Min)', expected_pos=3, rank=17
- window:
  - id=47, name='Tao Long: Gioco da Tavolo Strategico per 2 Giocatori - Duello di Dragoni e Movimento del Bagua - Durata 20 Minuti - Gate On Game'
  - id=37, name='Fantascatti Special - Gioco di Destrezza e Abilità per 4-8 Giocatori con Cappello Magico - Divertimento in Famiglia!'
  - id=34, name='Carcassonne - Nuova Edizione | Gioco Strategico per Famiglia, 2-5 Giocatori, 45 Minuti di Divertimento - Giochi Uniti'
  - id=54, name='King of Tokyo - Gioco da Tavolo di Strategia e Combattimento per 2-6 Giocatori, Edizione Rinnovata con Nuovi Mostri!'
  - id=45, name='Pot de Vin - Gioco di Carte Strategico per 3-6 Giocatori, Divertimento Tardo Medievale, Collezione e Inganno, 30 Minuti'
- note: Onitama is exact (2p, 10min, chess-like abstract) > Tao Long (2p, 20min abstract duel) > Spirits of the Forest (light abstract, but 1-4p and not a duel).

### pirati-navi-tesori
- ndcg: `0.4796`
- mean_displacement: `3.0`
- query: Un gioco di pirati, con le navi e la caccia al tesoro
- oracle:
  - id=46, name="Dead Man's Doubloons - Gioco di Avventura Pirata per 2-6 Giocatori, Combattimento e Strategia, 45 Minuti, Jason Miceli", expected_pos=1, rank=2
  - id=13, name='Ticket to Ride: Vagoni & Velieri', expected_pos=2, rank=7
- window:
  - id=39, name='La Festa per Odino: I Norvegesi - Espansione Gioco di Uwe Rosenberg, 1-4 Giocatori, Strategia e Avventura Vichinga, Cranio Creat'
  - id=46, name="Dead Man's Doubloons - Gioco di Avventura Pirata per 2-6 Giocatori, Combattimento e Strategia, 45 Minuti, Jason Miceli"
  - id=34, name='Carcassonne - Nuova Edizione | Gioco Strategico per Famiglia, 2-5 Giocatori, 45 Minuti di Divertimento - Giochi Uniti'
  - id=38, name='Schönbrunn - Gioco da Tavolo Strategico di Trattative Diplomatiche (3-6 Giocatori) - Storia e Politica del XIX Secolo'
- note: Dead Man's Doubloons is the only pirate game (ships, treasure race) > Ticket to Ride Vagoni & Velieri (the only other ships game, graded relevance only).

### fattoria-piazzamento-lavoratori
- ndcg: `0.735`
- mean_displacement: `8.67`
- query: Un gestionale di piazzamento lavoratori dove costruisco la mia fattoria con gli animali
- oracle:
  - id=29, name='Agricola - Gioco da Tavolo Strategico 1-4 Giocatori | Costruisci la Fattoria e Gestisci le Risorse | Asmodee', expected_pos=1, rank=3
  - id=22, name='Viticulture Essential Edition - Gioco Strategico di Piazzamento Lavoratori, 1-6 Giocatori, Gestione Vigna, Ghenos Games', expected_pos=2, rank=1
  - id=20, name='Stone Age: 10° Anniversario - Edizione Limitata | Gioco da Tavolo Strategico 2-4 Giocatori, 90 Minuti - Giochi Uniti', expected_pos=3, rank=26
- window:
  - id=22, name='Viticulture Essential Edition - Gioco Strategico di Piazzamento Lavoratori, 1-6 Giocatori, Gestione Vigna, Ghenos Games'
  - id=2, name="Lords of Hellas - Gioco da Tavolo Strategico di Mitologia Greca per 1-4 Giocatori, 120 Minuti d'Avventura, Adam Kwapinski"
  - id=29, name='Agricola - Gioco da Tavolo Strategico 1-4 Giocatori | Costruisci la Fattoria e Gestisci le Risorse | Asmodee'
  - id=34, name='Carcassonne - Nuova Edizione | Gioco Strategico per Famiglia, 2-5 Giocatori, 45 Minuti di Divertimento - Giochi Uniti'
  - id=7, name='Specie Dominanti - Gioco da Tavolo Preistorico di Strategia per 2-6 Giocatori, 120 Minuti di Divertimento e Competizione Asmodee'
- note: Agricola is the literal answer (farm + animals + worker placement) > Viticulture (a farm too, but a vineyard) > Stone Age (worker placement with farming, prehistoric civ). La Festa per Odino matches the theme but is an EXPANSION — if it outranks base games that is the anomaly to read.

### wargame-scifi-due-miniature
- ndcg: `0.7602`
- mean_displacement: `10.0`
- query: Un wargame di fantascienza con le miniature, per giocare in due
- oracle:
  - id=6, name='Star Wars: Legion - Gioco di Miniature Strategico per 2 Giocatori, 33 Miniature, Battaglie Epiche, 120 Min, Alex Davy, Asmodee', expected_pos=1, rank=1
  - id=16, name='Warhammer 40,000: Heroes of Black Reach - Gioco da Tavolo Strategico per 2 Giocatori, 90 Minuti di Battaglie Epiche in Italiano', expected_pos=2, rank=22
- window:
  - id=6, name='Star Wars: Legion - Gioco di Miniature Strategico per 2 Giocatori, 33 Miniature, Battaglie Epiche, 120 Min, Alex Davy, Asmodee'
  - id=1, name='Massive Darkness - Gioco Cooperativo Fantasy con Miniature | 1-6 Giocatori | Dungeon Crawler Avventura - Italiano Asmodee'
  - id=28, name='Talisman: Il Cataclisma - Espansione per 2-6 Giocatori, Avventure e Magia in un Mondo Fantastico! Combattimenti e Strategia!'
  - id=8, name='Dungeon Saga: La Missione del Re dei Nani - Gioco da Tavolo Fantasy per 2-5 Giocatori, Avventure e Combattimenti in Italiano'
- note: Star Wars Legion (2p sci-fi miniatures wargame, explicit miniatures) > Warhammer 40k Heroes of Black Reach (2p sci-fi wargame, counters/dice). Both fit; Legion is the stronger miniatures match.

### deck-building-dungeon
- ndcg: `0.7625`
- mean_displacement: `10.0`
- query: Un deck building d'avventura, esplorare un sotterraneo e arraffare tesori prima degli altri
- oracle:
  - id=27, name='Clank! - Gioco di Deck-Building Avventuroso per 2-4 Giocatori, Esplora la Fortezza del Drago, Voto GameNest 7.8, Italiano', expected_pos=1, rank=1
  - id=18, name='Altiplano di Giochix - Gioco di Strategia per 2-5 Giocatori, 120 Minuti di Avventure e Sfide in Alta Quota, Ideato da Reiner Sto', expected_pos=2, rank=31
  - id=33, name='Newton - Gioco da Tavolo Strategico per 2-4 Giocatori | Avventura nel Diciottesimo Secolo | Deckbuilding e Gestione della Mano', expected_pos=3, rank=2
- window:
  - id=27, name='Clank! - Gioco di Deck-Building Avventuroso per 2-4 Giocatori, Esplora la Fortezza del Drago, Voto GameNest 7.8, Italiano'
  - id=33, name='Newton - Gioco da Tavolo Strategico per 2-4 Giocatori | Avventura nel Diciottesimo Secolo | Deckbuilding e Gestione della Mano'
  - id=55, name='Kanagawa - Gioco da Tavolo Artistico per 2-4 Giocatori, Ispirato a Hokusai, 45 Minuti di Creatività e Strategia, Complessità M'
  - id=39, name='La Festa per Odino: I Norvegesi - Espansione Gioco di Uwe Rosenberg, 1-4 Giocatori, Strategia e Avventura Vichinga, Cranio Creat'
  - id=21, name='Terraforming Mars'
- note: Clank! is the literal answer (deck building + dungeon delve + treasure race) > Altiplano (bag building economy, no dungeon) > Newton (deck/pool building, scientific travel). The order of the last two is mechanical-affinity grading, a swap there is a minor deviation.

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
