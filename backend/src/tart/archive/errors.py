class ArchiveRuleViolation(ValueError):
    """A value or change that breaks an archive rule.

    `code` is stable: the API returns it with its parameters and the frontend
    translates it (ADR 0008).
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
