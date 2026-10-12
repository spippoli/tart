"""`/api/auth/*`: sign-in by email code or passkey, registration, the signed-in
User's account settings, email change, and passkeys, sessions (Foundations spec, 2).

Every answer to the code request is the same whatever the address; refusals carry
a translatable error code, `{"code": ...}`.
"""

import math
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import JSONResponse
from procrastinate import App
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine

from tart.auth import (
    LANGUAGE_UNAVAILABLE,
    SESSION_ABSOLUTE_LIFETIME,
    Authentication,
    CodeAttempt,
    CodeRequest,
    EmailChange,
    RateLimited,
    Refused,
    Registration,
    RegistrationRequired,
    accounts,
    passkeys,
    sessions,
)
from tart.auth.built_in import BuiltInAuthentication
from tart.auth.passkeys import RelyingParty
from tart.auth.sessions import COOKIE, SessionUser
from tart.auth.users import display_name_problem
from tart.config import Configuration

router = APIRouter(prefix="/api/auth")

CLIENT_IP_HEADER = "X-Tart-Client-IP"
"""Set by Caddy, the single trusted proxy, on every request it forwards, and by the
frontend's server from the same header. `X-Forwarded-For` is never read."""
RATE_LIMITED = "rate_limited"
SIGN_IN_REQUIRED = "sign_in_required"
PASSKEY_NOT_FOUND = "passkey_not_found"

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
        relying_party=RelyingParty.for_site(
            str(configuration.environment.PUBLIC_BASE_URL), settings.identity.name
        ),
        privacy_contact=settings.contacts.privacy,
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


def _rate_limited(outcome: RateLimited) -> JSONResponse:
    seconds = max(1, math.ceil(outcome.wait.total_seconds()))
    return JSONResponse(
        {"code": RATE_LIMITED, "retry_after": seconds},
        status_code=429,
        headers={"Retry-After": str(seconds)},
    )


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
        return _rate_limited(outcome)  # type: ignore[return-value]
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


def _sign_in_required() -> JSONResponse:
    return JSONResponse({"code": SIGN_IN_REQUIRED}, status_code=401)


class AccountState(BaseModel):
    number: int
    email: str
    display_name: str
    preferred_language: str


class AccountChange(BaseModel):
    display_name: str | None = None
    """1 to 40 characters after trimming, no control characters, not a deleted-account label."""
    preferred_language: str | None = None
    """An enabled UI language; it is also the language of the User's emails."""


async def _account(engine: AsyncEngine, user_id: int) -> AccountState:
    async with engine.begin() as connection:
        account = await accounts.read(connection, user_id)
    return AccountState(
        number=account.number,
        email=account.email,
        display_name=account.display_name,
        preferred_language=account.preferred_language,
    )


@router.get("/account", responses={401: {"model": Error}})
async def account(
    user: Annotated[SessionUser | None, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> AccountState:
    """The signed-in User's account settings."""
    if user is None:
        return _sign_in_required()  # type: ignore[return-value]
    return await _account(engine, user.id)


@router.patch("/account", responses={400: {"model": Error}, 401: {"model": Error}})
async def change_account(
    body: AccountChange,
    request: Request,
    user: Annotated[SessionUser | None, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    configuration: Annotated[Configuration, Depends(get_configuration)],
) -> AccountState:
    """Change the display name, the preferred UI language, or both."""
    if user is None:
        return _sign_in_required()  # type: ignore[return-value]
    ui_languages = configuration.instance.settings.languages.ui
    if body.display_name is not None:
        problem = display_name_problem(body.display_name, request.app.state.catalogue, ui_languages)
        if problem is not None:
            return JSONResponse({"code": problem}, status_code=400)  # type: ignore[return-value]
    if body.preferred_language is not None and body.preferred_language not in ui_languages:
        return JSONResponse({"code": LANGUAGE_UNAVAILABLE}, status_code=400)  # type: ignore[return-value]
    async with engine.begin() as connection:
        await accounts.change(
            connection,
            user.id,
            display_name=body.display_name and body.display_name.strip(),
            preferred_language=body.preferred_language,
        )
    return await _account(engine, user.id)


class EmailChangeBody(BaseModel):
    email: str
    """The new address."""


class EmailChangeCode(BaseModel):
    code: str


@router.post(
    "/account/email",
    status_code=202,
    responses={400: {"model": Error}, 401: {"model": Error}, 429: {"model": RateLimitedError}},
)
async def request_email_change(
    body: EmailChangeBody,
    request: Request,
    user: Annotated[SessionUser | None, Depends(current_user)],
    authentication: Annotated[Authentication, Depends(get_authentication)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict[str, str]:
    """Send a code to the new address; the answer is the same if another User has it."""
    if user is None:
        return _sign_in_required()  # type: ignore[return-value]
    outcome = await authentication.request_email_change(
        EmailChange(user.id, body.email, client_ip(request)), clock()
    )
    if isinstance(outcome, RateLimited):
        return _rate_limited(outcome)  # type: ignore[return-value]
    if isinstance(outcome, Refused):
        return JSONResponse({"code": outcome.code}, status_code=400)  # type: ignore[return-value]
    return {}


@router.post(
    "/account/email/verify",
    responses={400: {"model": Error}, 401: {"model": Error}},
)
async def confirm_email_change(
    body: EmailChangeCode,
    user: Annotated[SessionUser | None, Depends(current_user)],
    authentication: Annotated[Authentication, Depends(get_authentication)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> AccountState:
    """Change the address to the new one once its code is entered."""
    if user is None:
        return _sign_in_required()  # type: ignore[return-value]
    outcome = await authentication.confirm_email_change(user.id, body.code, clock())
    if isinstance(outcome, Refused):
        return JSONResponse({"code": outcome.code}, status_code=400)  # type: ignore[return-value]
    return await _account(engine, user.id)


class PasskeyCredential(BaseModel):
    credential: dict[str, Any]
    """The browser's `PublicKeyCredential`, in WebAuthn's JSON form (`toJSON()`)."""


@router.post("/passkey/options")
async def passkey_sign_in_options(
    authentication: Annotated[Authentication, Depends(get_authentication)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict[str, Any]:
    """WebAuthn options for signing in with a passkey of this site, valid 5 minutes."""
    return await authentication.passkey_sign_in_options(clock())


@router.post("/passkey/verify", responses={400: {"model": Error}})
async def passkey_sign_in(
    body: PasskeyCredential,
    response: Response,
    authentication: Annotated[Authentication, Depends(get_authentication)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> Verified:
    """Sign in with the passkey the browser used; any failure is `passkey_invalid`."""
    outcome = await authentication.sign_in_with_passkey(body.credential, clock())
    if isinstance(outcome, Refused):
        return JSONResponse({"code": outcome.code}, status_code=400)  # type: ignore[return-value]
    _set_session_cookie(response, outcome.session_token)
    return Verified(outcome="signed_in")


class PasskeySummary(BaseModel):
    id: int
    name: str
    created_at: datetime


class NewPasskey(PasskeyCredential):
    name: str
    """1 to 40 characters after trimming, no control characters."""


@router.get("/passkeys", responses={401: {"model": Error}})
async def list_passkeys(
    user: Annotated[SessionUser | None, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> list[PasskeySummary]:
    """The signed-in User's passkeys, oldest first; never any key material."""
    if user is None:
        return _sign_in_required()  # type: ignore[return-value]
    async with engine.begin() as connection:
        found = await passkeys.list_for(connection, user.id)
    return [PasskeySummary(id=key.id, name=key.name, created_at=key.created_at) for key in found]


@router.post("/passkeys/options", responses={401: {"model": Error}})
async def passkey_registration_options(
    user: Annotated[SessionUser | None, Depends(current_user)],
    authentication: Annotated[Authentication, Depends(get_authentication)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict[str, Any]:
    """WebAuthn options for adding a passkey to the signed-in User, valid 5 minutes."""
    if user is None:
        return _sign_in_required()  # type: ignore[return-value]
    return await authentication.passkey_registration_options(user.id, clock())


@router.post("/passkeys", status_code=201, responses={400: {"model": Error}, 401: {"model": Error}})
async def add_passkey(
    body: NewPasskey,
    user: Annotated[SessionUser | None, Depends(current_user)],
    authentication: Annotated[Authentication, Depends(get_authentication)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> PasskeySummary:
    """Add the passkey the browser created from the options."""
    if user is None:
        return _sign_in_required()  # type: ignore[return-value]
    outcome = await authentication.register_passkey(user.id, body.name, body.credential, clock())
    if isinstance(outcome, Refused):
        return JSONResponse({"code": outcome.code}, status_code=400)  # type: ignore[return-value]
    return PasskeySummary(id=outcome.id, name=outcome.name, created_at=outcome.created_at)


@router.delete(
    "/passkeys/{passkey_id}",
    status_code=204,
    responses={401: {"model": Error}, 404: {"model": Error}},
)
async def remove_passkey(
    passkey_id: int,
    user: Annotated[SessionUser | None, Depends(current_user)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> None:
    """Remove one of the signed-in User's passkeys."""
    if user is None:
        return _sign_in_required()  # type: ignore[return-value]
    async with engine.begin() as connection:
        removed = await passkeys.remove(connection, user.id, passkey_id)
    if not removed:
        return JSONResponse({"code": PASSKEY_NOT_FOUND}, status_code=404)  # type: ignore[return-value]
