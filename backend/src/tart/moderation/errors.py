class ModerationError(ValueError):
    """A request the moderation rules refuse.

    `code` is stable: the API returns it and the frontend translates it (ADR 0008).
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
