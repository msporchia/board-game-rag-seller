<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — ChatPitch — pitch()

> fallback_rate **0.000** · 12 cases · model `llama3.1` · session 20260611-123033

```
  Cases: 12

  fallback_rate           0/12 0.000 → (Δ +0.000, was: 0.000)   [all cases — lower is better]
  games_within_k         11/12 0.917 ↑ (Δ +0.083, was: 0.833)   [non-fallback replies]
  guided_asks_question    2/3  0.667 ↓ (Δ -0.333, was: 1.000)   [non-fallback GUIDED]
  quick_match_proposes    3/3  1.000 → (Δ +0.000, was: 1.000)   [non-fallback QUICK_MATCH, >=3 hits]
  beginner_jargon_free    5/5  1.000 → (Δ +0.000, was: 1.000)   [non-fallback beginner]

  ✗ guided-beginner-regalo-famiglia: guided_asks_question
  ✗ guided-beginner-coppia-serata: games_within_k
```

## Failures (2)

### GUIDED — guided-beginner-regalo-famiglia
- failed:
  - guided_asks_question
- expertise_level: beginner
- request: Ciao! Vorrei fare un regalo ai miei cugini per Natale, giocano poco ai giochi da tavolo... non so proprio da dove cominciare, mi aiuti?
- hits:
  - Dixit
  - Codenames
  - Carcassonne
  - Ticket to Ride
  - Azul
- reply_message: Ciao! Sembra che i tuoi cugini non giocino molto ai giochi da tavolo, quindi cercherò di consigliare qualcosa di facile e divertente per loro. Ecco due opzioni che potrebbero piacere! Dixit è un gioco di racconti che è come una grande partita di 'indovina chi è'. Ognuno dei giocatori deve descrivere la propria immagine senza dire il suo titolo e gli altri devono indovinare chi è. È facile da capire, ma richiede un po' di immaginazione! Codenames è un gioco di squadra in cui i giocatori sono divisi in due squadre e devono trovare le parole che corrispondono ai nomi dati dai loro leader. È una sfida divertente per la mente!
- reply_games:
  - Dixit
  - Codenames
- reply_quick_replies:
  - Sorprendimi
  - Per 2 giocatori
- note: Undecided beginner gift-shopper, first turn: GUIDED should narrow to 1-2 clear options and close with one simple question, jargon-free.

### GUIDED — guided-beginner-coppia-serata
- failed:
  - games_within_k
- expertise_level: beginner
- request: Mah, non saprei... forse tranquillo? Però non vorrei che ci annoiassimo, boh.
- hits:
  - Patchwork
  - Splendor
  - Carcassonne
  - Azul
- reply_message: Ecco, allora! Ho capito che volete qualcosa di tranquillo ma non troppo noioso. Ecco due opzioni che potrebbero essere adatte a voi e al vostro ragazzo. Patchwork è un gioco di piazzamento tessere divertente e rilassante. Potrete costruire insieme una bellissima patchwork, creando un paesaggio unico. Splendor è un gioco di gestione delle risorse che vi farà sentire come principi del Medioevo. Avete bisogno di più tempo per costruire il vostro impero? Azul è un gioco di pattern building abbastanza tranquillo ma con una sfida interessante. Siete pronti a sfidarvi in una gara di produzione di piastrelle?
- reply_games:
  - Patchwork
  - Splendor
  - Azul
- reply_quick_replies:
  - Sorprendimi
  - Per 2 giocatori
  - Max 60 minuti
- note: Hesitant beginner couple mid-conversation: GUIDED with history; the wavering answer must produce a narrowing question, not a wall of options.

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
