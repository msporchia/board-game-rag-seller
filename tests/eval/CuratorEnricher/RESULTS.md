<!-- Auto-generated at eval session end (tests/eval/report). Do not edit. -->
# Eval — Curator — assess()

> F1 **0.552** · P 0.571 / R 0.533 · model `llama3.1` · session 20260611-123156

```
  Slots evaluated: 45 (skip structurally-present: 25)
  TP=16  FP=12  FN=14  TN=3

  Precision: 0.571 ↓ (Δ -0.095, was: 0.667)
  Recall: 0.533 ↑ (Δ +0.004, was: 0.529)
  F1       : 0.552 ↓ (Δ -0.038, was: 0.590)
  F0.5     : 0.563 ↓ (Δ -0.070, was: 0.634)
  F0.25    : 0.569 ↓ (Δ -0.088, was: 0.657)

  slot                           TP  FP  FN  TN
  ambientazione/tema              8   2   0   0
  genere                          3   4   3   0
  a chi è adatto                  2   3   3   2
  meccaniche principali           0   0   0   0
  numero giocatori                2   0   2   1
  durata                          0   2   3   0
  complessità                     1   1   3   0

  ✗ dungeon-saga-real-gap.genere: FP (llm: "gioco strategico")
  ✗ dungeon-saga-real-gap.a chi è adatto: FP (llm: "famiglie")
  ✗ massive-darkness-complexity-in-text.genere: FN
  ✗ lords-of-hellas-duration-in-text.genere: FP (llm: "fantasy")
  ✗ lords-of-hellas-duration-in-text.a chi è adatto: FN
  ✗ lords-of-hellas-duration-in-text.durata: FP (llm: "120 minuti")
  ✗ pandemic-no-players.ambientazione/tema: FP (llm: "fantasy")
  ✗ pandemic-no-players.genere: FN
  ✗ pandemic-no-players.a chi è adatto: FP (llm: "famiglie")
  ✗ pandemic-no-players.numero giocatori: FN
  ✗ case-follia-doubly-missing.durata: FN
  ✗ case-follia-doubly-missing.complessità: FP (llm: "cooperativo")
  ✗ star-wars-doubly-missing.ambientazione/tema: FP (llm: "fantasy")
  ✗ star-wars-doubly-missing.a chi è adatto: FP (llm: "famiglie")
  ✗ star-wars-doubly-missing.numero giocatori: FN
  ✗ star-wars-doubly-missing.complessità: FN
  ✗ specie-dominanti-no-duration.genere: FP (llm: "gioco da tavolo")
  ✗ specie-dominanti-no-duration.durata: FN
  ✗ mercanti-stripped-all-structured.genere: FP (llm: "strategico")
  ✗ mercanti-stripped-all-structured.a chi è adatto: FN
  ✗ mercanti-stripped-all-structured.durata: FP (llm: "120 minuti")
  ✗ mercanti-stripped-all-structured.complessità: FN
  ✗ dixit-complexity-in-text.genere: FN
  ✗ dixit-complexity-in-text.a chi è adatto: FN
  ✗ dixit-complexity-in-text.complessità: FN
  ✗ onitama-doubly-missing.durata: FN
```

## Failures (10)

### dungeon-saga-real-gap
- slots: genere={'outcome': 'FP', 'oracle': ['cooperativ', 'avventur'], 'llm_value': 'gioco strategico'}, a chi è adatto={'outcome': 'FP', 'oracle': ['neofiti', 'veterani'], 'llm_value': 'famiglie'}

### massive-darkness-complexity-in-text
- slots: genere={'outcome': 'FN', 'oracle': ['cooperativo'], 'llm_value': None}

### lords-of-hellas-duration-in-text
- slots: genere={'outcome': 'FP', 'oracle': ['strategi', 'gestional'], 'llm_value': 'fantasy'}, a chi è adatto={'outcome': 'FN', 'oracle': ['esperti'], 'llm_value': None}, durata={'outcome': 'FP', 'oracle': ['75'], 'llm_value': '120 minuti'}

### pandemic-no-players
- slots: ambientazione/tema={'outcome': 'FP', 'oracle': ['pandemia', 'epidem', 'globale'], 'llm_value': 'fantasy'}, genere={'outcome': 'FN', 'oracle': ['cooperativ', 'collaborativ'], 'llm_value': None}, a chi è adatto={'outcome': 'FP', 'oracle': None, 'llm_value': 'famiglie'}, numero giocatori={'outcome': 'FN', 'oracle': ['2', '4'], 'llm_value': None}

### case-follia-doubly-missing
- slots: durata={'outcome': 'FN', 'oracle': ['150'], 'llm_value': None}, complessità={'outcome': 'FP', 'oracle': ['medi'], 'llm_value': 'cooperativo'}

### star-wars-doubly-missing
- slots: ambientazione/tema={'outcome': 'FP', 'oracle': ['star wars', 'fantascien', 'galatti'], 'llm_value': 'fantasy'}, a chi è adatto={'outcome': 'FP', 'oracle': None, 'llm_value': 'famiglie'}, numero giocatori={'outcome': 'FN', 'oracle': ['2', '2'], 'llm_value': None}, complessità={'outcome': 'FN', 'oracle': ['medi', 'pesante'], 'llm_value': None}

### specie-dominanti-no-duration
- slots: genere={'outcome': 'FP', 'oracle': ['gestional', 'strategi'], 'llm_value': 'gioco da tavolo'}, durata={'outcome': 'FN', 'oracle': ['180'], 'llm_value': None}

### mercanti-stripped-all-structured
- slots: genere={'outcome': 'FP', 'oracle': ['gestional', 'esplora', 'economi'], 'llm_value': 'strategico'}, a chi è adatto={'outcome': 'FN', 'oracle': ['famigli'], 'llm_value': None}, durata={'outcome': 'FP', 'oracle': ['180'], 'llm_value': '120 minuti'}, complessità={'outcome': 'FN', 'oracle': ['medi'], 'llm_value': None}

### dixit-complexity-in-text
- slots: genere={'outcome': 'FN', 'oracle': ['storytelling', 'party', 'narra'], 'llm_value': None}, a chi è adatto={'outcome': 'FN', 'oracle': ['famigli'], 'llm_value': None}, complessità={'outcome': 'FN', 'oracle': ['leggero'], 'llm_value': None}

### onitama-doubly-missing
- slots: durata={'outcome': 'FN', 'oracle': ['10'], 'llm_value': None}

The cases live in [fixtures/](fixtures/) (each one carries its oracle `note`); the machine-readable history stays in `runs/` (local, gitignored).
