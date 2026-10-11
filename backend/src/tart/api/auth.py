"""`/api/auth/*`: sign-in by email code, registration, sessions (Foundations spec, 2).

Every answer to the code request is the same whatever the address; refusals carry
a translatable error code, `{"code": ...}`.
"""

import math
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import JSONResponse
from procrastinate import App
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine

from tart.auth import (
    SESSION_ABSOLUTE_LIFETIME,
    Authentication,
    CodeAttempt,
    CodeRequest,
    RateLimited,
    Refused,
    Registration,
    RegistrationRequired,
    sessions,
)
from tart.auth.built_in import BuiltInAuthentication
from tart.auth.sessions import COOKIE, SessionUser
from tart.config import Configuration

router = APIRouter(prefix="/api/auth")

CLIENT_IP_HEADER = "X-Tart-Client-IP"
"""Set by Caddy, the single trusted proxy, on every request it forwards, and by the
frontend's server from the same header. `X-Forwarded-For` is never read."""
RATE_LIMITED = "rate_limited"
SIGN_IN_REQUIRED = "sign_in_required"

Clock = Callable[[], datetime]


def system_clock() -> datetime:
    return datetime.now(UTC)


def get_clock() -> Clock:
    return system_clock


def get_configuration(request: Request) -> Configuration:
    return request.app.state.configuration


def get_engine(request: Request) -> AsyncEngine:
    return request.app.state.engine


def get_jobs(request: Request) -> App:
    return request.app.state.jobs


def get_key(configuration: Annotated[Configuration, Depends(get_configuration)]) -> bytes:
    return configuration.environment.SESSION_KEY.get_secret_value().encode()


def get_authentication(
    request: Request,
    configuration: Annotated[Configuration, Depends(get_configuration)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    jobs: Annotated[App, Depends(get_jobs)],
    key: Annotated[bytes, Depends(get_key)],
) -> Authentication:
    settings = configuration.instance.settings
    return BuiltInAuthentication(
        engine=engine,
        jobs=jobs,
        key=key,
        registration=settings.community.registration,
        ui_languages=settings.languages.ui,
        catalogue=request.app.state.catalogue,
    )


def client_ip(request: Request) -> str:
    forwarded = request.headers.get(CLIENT_IP_HEADER)
    if forwarded:
        return forwarded.strip()
    return request.client.host if request.client else "unknown"


async def current_user(
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
    key: Annotated[bytes, Depends(get_key)],
    token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
) -> SessionUser | None:
    """The signed-in User of the request, or None."""
    if not token:
        return None
    async with engine.begin() as connection:
        return await sessions.resolve(connection, token, clock(), key)


class Error(BaseModel):
    code: str


class RateLimitedError(BaseModel):
    code: Literal["rate_limited"]
    retry_after: int
    """Seconds to wait before asking again."""


class CodeRequestBody(BaseModel):
    email: str
    language: str
    """The UI language of the sign-in page."""
    website: str = ""
    """The honeypot: people leave it empty."""


@router.post(
    "/code",
    status_code=202,
    responses={400: {"model": Error}, 429: {"model": RateLimitedError}},
)
async def request_code(
    body: CodeRequestBody,
    request: Request,
    authentication: Annotated[Authentication, Depends(get_authentication)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict[str, str]:
    """Send a one-time code to the address, or what the address gets instead; the
    answer never says which addresses have accounts."""
    outcome = await authentication.request_code(
        CodeRequest(body.email, body.language, client_ip(request), body.website), clock()
    )
    if isinstance(outcome, RateLimited):
        seconds = max(1, math.ceil(outcome.wait.total_seconds()))
        return JSONResponse(  # type: ignore[return-value]
            {"code": RATE_LIMITED, "retry_after": seconds},
            status_code=429,
            headers={"Retry-After": str(seconds)},
        )
    if isinstance(outcome, Refused):
        return JSONResponse({"code": outcome.code}, status_code=400)  # type: ignore[return-value]
    return {}


class RegistrationBody(BaseModel):
    display_name: str
    age_confirmed: bool


class CodeAttemptBody(BaseModel):
    email: str
    code: str
    language: str
    registration: RegistrationBody | None = None


class Verified(BaseModel):
    outcome: Literal["signed_in", "registration_required"]


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE,
        token,
        max_age=int(SESSION_ABSOLUTE_LIFETIME.total_seconds()),
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/", secure=True, httponly=True, samesite="lax")


@router.post("/code/verify", responses={400: {"model": Error}})
async def verify_code(
    body: CodeAttemptBody,
    response: Response,
    authentication: Annotated[Authentication, Depends(get_authentication)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> Verified:
    """Check the code: sign in, ask for the registration step (send it again with the
    code and `registration`), or refuse with an error code."""
    registration = body.registration and Registration(
        body.registration.display_name, body.registration.age_confirmed
    )
    outcome = await authentication.verify_code(
        CodeAttempt(body.email, body.code, body.language, registration), clock()
    )
    if isinstance(outcome, Refused):
        return JSONResponse({"code": outcome.code}, status_code=400)  # type: ignore[return-value]
    if isinstance(outcome, RegistrationRequired):
        return Verified(outcome="registration_required")
    _set_session_cookie(response, outcome.session_token)
    return Verified(outcome="signed_in")


class SignedInUser(BaseModel):
    number: int
    display_name: str
    preferred_language: str
    moderator: bool


class SessionState(BaseModel):
    user: SignedInUser | None


@router.get("/session")
async def session(
    user: Annotated[SessionUser | None, Depends(current_user)],
) -> SessionState:
    """The signed-in User, or null; the frontend's server asks on every page."""
    if user is None:
        return SessionState(user=None)
    return SessionState(
        user=SignedInUser(
            number=user.id,
            display_name=user.display_name,
            preferred_language=user.preferred_language,
            moderator=user.moderator,
        )
    )


@router.post("/sign-out", status_code=204)
async def sign_out(
    response: Response,
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    key: Annotated[bytes, Depends(get_key)],
    token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
) -> None:
    """End this session."""
    if token:
        async with engine.begin() as connection:
            await sessions.revoke(connection, token, key)
    _clear_session_cookie(response)


@router.post("/sign-out-everywhere", status_code=204, responses={401: {"model": Error}})
async def sign_out_everywhere(
    response: Response,
    user: Annotated[SessionUser | None, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> None:
    """End every session of the signed-in User, this one included."""
    if user is None:
        return JSONResponse({"code": SIGN_IN_REQUIRED}, status_code=401)  # type: ignore[return-value]
    async with engine.begin() as connection:
        await sessions.revoke_all(connection, user.id)
    _clear_session_cookie(response)
