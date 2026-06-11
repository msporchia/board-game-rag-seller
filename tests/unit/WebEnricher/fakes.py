class NoSearch:
    """Inert search provider: no network call in the deterministic tests."""

    def search(self, *args, **kwargs):
        return []
