"""The 429 answer of the per-User contribution limits: a translatable error code and the time
from which the action is possible again (contribution spec, Rate limits)."""

import math
from datetime import timedelta

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class LimitedError(BaseModel):
    code: str
    """`moderation.submissions_limited`, `moderation.drafts_limited`, or
    `moderation.uploads_limited`."""
    retry_after: int
    """Seconds to wait before the action is possible again."""


def limited(code: str, wait: timedelta) -> JSONResponse:
    seconds = max(1, math.ceil(wait.total_seconds()))
    return JSONResponse(
        {"code": code, "retry_after": seconds},
        status_code=429,
        headers={"Retry-After": str(seconds)},
    )
