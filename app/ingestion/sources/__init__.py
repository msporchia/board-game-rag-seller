"""Data sources: produce GameDoc from an external source. One class per module:

- `source.GameSource`: the abstract base — to add a new source (e.g. BGG, other catalogs)
  you only need a subclass that implements `fetch()` and maps to the canonical GameDoc model.
- `prestashop.PrestashopSource`: the live catalog (PrestaShop `controller=seller` endpoint).
- `json_source.JsonSource`: list of DTO dicts or a JSON file — reproducible/offline (tests,
  interim export).
"""
