"""The per-User limits of the contribution spec (Rate limits), counted by the Foundations
rate-limit module. They are platform constants, not Instance configuration; Moderators are
exempt from all three.
"""

from datetime import timedelta

from tart.rate_limits import Limit

SUBMISSIONS = Limit("contribution_submit", 20, timedelta(hours=24))
"""A submission or resubmission; a revision of a `submitted` Submission is not counted."""
UPLOAD_FILES = Limit("upload_files", 100, timedelta(hours=24))
"""File uploads, rejected files included."""
UPLOAD_BYTES = Limit("upload_bytes", 1024**3, timedelta(hours=24))
"""The bytes of the uploads, 1 GB per 24 hours, counted from the size the request declares."""
OPEN_DRAFTS = 20
"""Open drafts at once, retry and conversion drafts included."""

SUBMISSIONS_LIMITED = "moderation.submissions_limited"
DRAFTS_LIMITED = "moderation.drafts_limited"
UPLOADS_LIMITED = "moderation.uploads_limited"


class LimitReached(Exception):
    """A per-User limit refuses the action; `wait` is the time until it may be done."""

    def __init__(self, code: str, wait: timedelta) -> None:
        super().__init__(code)
        self.code = code
        self.wait = wait
