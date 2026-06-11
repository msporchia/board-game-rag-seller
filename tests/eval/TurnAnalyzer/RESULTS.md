<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — TurnAnalyzer — analyze

> micro-accuracy **0.870** · 54 cases · model `llama3.1` · session 20260611-122821

```
  Cases: 54   micro-accuracy: 0.870 → (Δ +0.000, was: 0.870)

  decisiveness       10/12  0.833 → (Δ +0.000, was: 0.833)
                       ✗ voglio-catan-ce-l-avete: decided -> moderate
                       ✗ ticket-to-ride-quale-versione: moderate -> undecided
  enthusiasm         12/12  1.000 → (Δ +0.000, was: 1.000)
  escalate            8/10  0.800 → (Δ +0.000, was: 0.800)
                       ✗ lo-prendo-subito-quale-dei-due: True -> False
                       ✗ regalo-urgente-compleanno: True -> False
  expertise_level     9/12  0.750 → (Δ +0.000, was: 0.750)
                       ✗ worker-placement-peso-bgg: advanced -> intermediate
                       ✗ controllo-aree-interazione: advanced -> intermediate
                       ✗ eurogamer-prova-ameritrash: advanced -> intermediate
  reply_style         8/8   1.000 → (Δ +0.000, was: 1.000)
```

## Failures (7)

### decisiveness — voglio-catan-ce-l-avete
- expected: decided
- got: moderate
- message: Voglio Catan, ce l'avete?
- note: First turn, names one specific game and asks for availability: nothing to clarify, ready to buy.
- model_read: enthusiasm='medium', decisiveness='moderate', expertise_level='intermediate', reply_style='short', escalate=False, escalation_reason='Il cliente ha espresso una preferenza per un titolo specifico (Catan) ma non sembra avere intenzione di acquistare immediatamente.', confidence=0.7

### decisiveness — ticket-to-ride-quale-versione
- expected: moderate
- got: undecided
- conversation:
  - utente: vorrei un gioco da fare con i miei figli di 10 e 12 anni
  - bot: Ticket to Ride è una scelta molto adatta a quell'età: si collegano città con vagoni colorati, le regole si imparano in dieci minuti.
- message: Volevo prendere proprio quello, però ho visto che ci sono tante versioni e non so quale scegliere.
- note: Boundary case: committed to the game family, undecided on which edition.
- model_read: enthusiasm='medium', decisiveness='undecided', expertise_level='intermediate', reply_style='short', escalate=False, escalation_reason='il cliente ha espresso un dubbio sulla scelta del gioco e non sembra avere una preferenza chiara', confidence=0.6

### escalate — lo-prendo-subito-quale-dei-due
- expected: `True`
- got: `False`
- conversation:
  - utente: Cerco un gioco veloce da fare in due con la mia ragazza
  - bot: Ti propongo due classici moderni: Azul, astratto ed elegante, oppure Splendor, motore di gemme molto scorrevole. Entrambi girano benissimo in due.
  - utente: Belli entrambi, lei ama le cose colorate
- message: Dai, lo prendo subito: quale dei due mi consigli tra Azul e Splendor?
- note: Boundary true: no budget stated, but explicit immediate purchase intent choosing between two proposals.
- model_read: enthusiasm='medium', decisiveness='decided', expertise_level='intermediate', reply_style='short', escalate=False, escalation_reason='il cliente ha già scelto un titolo e chiede una raccomandazione tra due opzioni specifiche', confidence=0.8

### escalate — regalo-urgente-compleanno
- expected: `True`
- got: `False`
- message: Aiuto, il compleanno di mia moglie è domani e non ho ancora niente! Siamo 4 adulti, massimo 40 euro: cosa avete di pronto da incartare?
- note: Urgency (tomorrow) plus budget and player count, already at the first message.
- model_read: enthusiasm='medium', decisiveness='moderate', expertise_level='intermediate', reply_style='short', escalate=False, escalation_reason='Il cliente ha un problema specifico da risolvere (trovare un gioco per il compleanno della moglie) e richiede una soluzione entro un certo budget. Non sembra avere bisogno di informazioni dettagliate o confronti tra titoli.', confidence=0.8

### expertise_level — worker-placement-peso-bgg
- expected: advanced
- got: intermediate
- message: Cerco un worker placement con peso BGG sopra 3, magari con una componente di engine building; ho già Agricola e Caverna quindi qualcosa di diverso.
- note: Precise hobbyist jargon (worker placement, engine building, BGG weight) plus ownership of heavy euros.
- model_read: enthusiasm='medium', decisiveness='moderate', expertise_level='intermediate', reply_style='long', escalate=False, escalation_reason="il cliente ha già un'idea precisa di cosa vuole ma non è ancora deciso e richiede ulteriore informazione", confidence=0.8

### expertise_level — controllo-aree-interazione
- expected: advanced
- got: intermediate
- conversation:
  - utente: cerco qualcosa di nuovo per il mio gruppo di gioco del giovedì
  - bot: Che tipo di giochi girano di solito al vostro tavolo?
- message: Preferisco i giochi di controllo aree e maggioranze, con interazione diretta: il multiplayer solitaire alla lunga mi annoia.
- note: Uses niche analytical terms (controllo aree, maggioranze, multiplayer solitaire) that only an experienced hobbyist would use.
- model_read: enthusiasm='medium', decisiveness='moderate', expertise_level='intermediate', reply_style='long', escalate=False, escalation_reason='il cliente ha espresso una preferenza per un tipo di gioco ma non ha ancora scelto un titolo specifico', confidence=0.7

### expertise_level — eurogamer-prova-ameritrash
- expected: advanced
- got: intermediate
- message: Nella mia collezione ho quasi solo eurogame a punti vittoria, vorrei provare un ameritrash con dadi e miniature, e non mi spaventano setup lunghi.
- note: Talks about a collection, contrasts euro vs ameritrash by design philosophy, accepts long setup — deep hobby fluency.
- model_read: enthusiasm='medium', decisiveness='moderate', expertise_level='intermediate', reply_style='long', escalate=False, escalation_reason='il cliente ha espresso una preferenza per un tipo di gioco (ameritrash) e ha fornito alcuni criteri per la scelta del titolo, ma non sembra avere una scelta precisa in mente.', confidence=0.7

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
