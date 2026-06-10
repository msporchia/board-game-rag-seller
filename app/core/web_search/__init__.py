"""Web search + fetch for the WebEnricher — one class per module, import what you need:

  - `result.SearchResult`: one search hit (discovery DTO).
  - `provider.WebSearchProvider`: "throw a query at an engine, get back URLs" (swappable ABC).
  - `ddgs.DdgsSearch`: default provider (free, no API key); in prod you swap in Tavily/Brave.
  - `fetcher.PageFetcher`: downloads a page with a browser User-Agent (many sources block
    "bare" fetchers: 403/401) and extracts the clean text (trafilatura). Injectable, so tests
    replace it instead of monkeypatching.

NO LLM here: just network I/O. The logic (whitelist, judgment, extraction) lives in the
WebEnricher.
"""
