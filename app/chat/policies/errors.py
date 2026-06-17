"""Policy errors. Mirrors app/rag/filters/errors.py for symmetry.

`PolicySet.from_names` logs-and-skips unknown names rather than raising (a customer turn must
never 500 on a caller typo); this exception exists for a future strict resolution mode.
"""


class UnknownPolicyError(KeyError):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name

    def __str__(self) -> str:
        return f"unknown policy: {self.name!r}"
