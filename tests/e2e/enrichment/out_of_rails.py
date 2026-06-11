class OutOfRailsError(RuntimeError):
    """The frozen scraping tried something the fixtures don't cover. Almost always: the
    webscraper (query/ranking/fetch) changed and the e2e fixtures are stale → re-record with
    `python -m tests.e2e.enrichment record`."""
