# CLAUDE.md

## Code structure convention

- **Folder = cohesive concept.** Related classes live as sibling modules inside one package
  (see `app/rag/filters/` — the reference example).
- **One class per file.** A small *private* helper class that exists only to serve the file's
  protagonist may cohabit; anything used from outside gets its own module.
- **`__init__.py` stays empty.** No re-export facades: importing one name would execute the
  whole package and re-create the circular imports the split exists to prevent.
- **Deep, explicit imports.** Import exactly what you need from the module that defines it:
  `from app.core.web_search.fetcher import PageFetcher` — never from the package root.
- **No loose functions beside classes.** Anything with behavior (I/O, state, swappable policy)
  is a class, injectable via constructor. Pure data manipulation belongs as a method on the
  model it manipulates.
- **Pre-split early.** Schema/model modules grow; start them as packages instead of splitting
  later under pressure.
- **Tests follow the same rule.** Directory = class under test, file = method/aspect, one
  `Test*` class per file. Fakes/helpers live in dedicated modules, conftest keeps fixtures only.

## Language

- Code, comments, docs, commit messages: English.
- LLM prompts and catalog-facing strings are intentionally Italian (Italian-catalog system) —
  do not translate them.

## Tooling

- Run lint/tests through Docker, never a local venv:
  - `docker compose exec seller-api python -m pytest tests/unit -q` (deterministic, offline)
  - `ruff` via its Docker image or compose service.
