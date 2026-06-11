class UnknownFilterError(ValueError):
    """Raised when a spec names a filter not in the REGISTRY (see search_filters)."""
