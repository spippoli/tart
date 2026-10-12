"""Health endpoints (Operations and portability spec, 5. Monitoring).

`GET /api/health` is public, for the Operator's external monitor: only `ok` or
`fail`, as 200 or 503, with no check names, values, or personal data.
`GET /api/health/details` needs `Authorization: Bearer <HEALTH_DETAILS_TOKEN>` and
lists every check with its value and threshold; `tart upgrade` reads its readiness
checks there.

A report is reused for `CACHE_SECONDS`, so that a busy monitor, or anyone polling the
public endpoint, does not run the checks (a storage write among them) on every request.
"""

import hmac
import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from tart import health
from tart.api.auth import Clock, get_clock

router = APIRouter(prefix="/api/health")

CACHE_SECONDS = 10.0
_bearer = HTTPBearer(auto_error=False)


class HealthCheck(BaseModel):
    key: str
    status: Literal["ok", "warning", "fail"]
    value: int | float | str | None
    """Untranslated; `null` when the check could not be read."""
    threshold: int | float | str
    unit: str | None


class HealthDetails(BaseModel):
    status: Literal["ok", "fail"]
    checks: list[HealthCheck]


def get_cache_seconds() -> float:
    return CACHE_SECONDS


async def current_report(
    request: Request,
    clock: Annotated[Clock, Depends(get_clock)],
    cache_seconds: Annotated[float, Depends(get_cache_seconds)],
) -> health.Report:
    state = request.app.state
    cached: tuple[float, health.Report] | None = getattr(state, "health_report", None)
    if cached is not None and time.monotonic() - cached[0] < cache_seconds:
        return cached[1]
    report = await health.run_checks(
        health.Services(state.engine, state.storage), state.health_settings, clock()
    )
    state.health_report = (time.monotonic(), report)
    return report


@router.get(
    "",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/plain": {"example": "ok"}}}, 503: {"description": "fail"}},
)
async def health_status(report: Annotated[health.Report, Depends(current_report)]) -> Response:
    """`ok` (200) or `fail` (503): `fail` while any check fails."""
    failing = report.status is health.Status.FAIL
    return PlainTextResponse(report.status.value, status_code=503 if failing else 200)


@router.get(
    "/details",
    response_model=HealthDetails,
    responses={401: {"description": "Missing or wrong token"}},
)
async def health_details(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    report: Annotated[health.Report, Depends(current_report)],
) -> HealthDetails | Response:
    """Every check, with its value and threshold, for the Operator."""
    token = request.app.state.configuration.environment.HEALTH_DETAILS_TOKEN
    if (
        token is None
        or credentials is None
        or not hmac.compare_digest(
            credentials.credentials.encode(), token.get_secret_value().encode()
        )
    ):
        return Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})
    return HealthDetails(
        status=report.status.value,
        checks=[
            HealthCheck(
                key=check.key,
                status=check.status.value,
                value=check.value,
                threshold=check.threshold,
                unit=check.unit,
            )
            for check in report.checks
        ],
    )
