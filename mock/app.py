"""Mock PrestaShop "seller" endpoint: serves the enriched-product DTO contract as JSON.

Lets the Seller microservice run without a real PrestaShop/MySQL stack: it replays a fixed
catalog (the bundled, scrubbed demo fixtures) over the same contract `PrestashopSource`
expects:

    GET /index.php?fc=module&module=utils&controller=seller&page=1&pageSize=100
    → {"products": [DTO, ...], "page": 1, "pageSize": 100, "hasNext": false}

Unknown query params (fc, module, controller, token, lastUpdateFrom, ids) are ignored.
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, Query

GAMES_FILE = os.environ.get("GAMES_FILE", "/data/games.json")
_GAMES: list[dict] = json.loads(Path(GAMES_FILE).read_text(encoding="utf-8"))

app = FastAPI(title="Mock PrestaShop (seller contract)")


@app.get("/health")
def health():
    return {"status": "ok", "games": len(_GAMES)}


@app.get("/index.php")
def seller(page: int = Query(1, ge=1), pageSize: int = Query(100, ge=1)):
    start = (page - 1) * pageSize
    chunk = _GAMES[start:start + pageSize]
    return {
        "products": chunk,
        "page": page,
        "pageSize": pageSize,
        "hasNext": start + pageSize < len(_GAMES),
    }
