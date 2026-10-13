"""Authentication: email one-time codes, registration, passkeys, and sessions (ADR 0005).

    outcome = await authentication.request_code(CodeRequest(...), now)
    outcome = await authentication.verify_code(CodeAttempt(...), now)
    outcome = await authentication.sign_in_with_passkey(credential, now)
    outcome = await authentication.request_email_change(EmailChange(...), now)

The API sees only the `Authentication` interface, so that a later Instance can
plug in an external identity provider; `BuiltInAuthentication`
(`tart.auth.built_in`) is the one implementation, and the method is not
configurable. Sessions and roles belong to TART whatever the method
(`tart.auth.sessions`).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from tart.auth.passkeys import Passkey

# Platform constants, which configuration cannot weaken (Foundations spec,
# Instance configuration). The code length is `tart.auth.tokens.CODE_LENGTH`.
CODE_LIFETIME = timedelta(minutes=10)
CODE_WRONG_ATTEMPTS = 5
SESSION_IDLE_LIFETIME = timedelta(days=30)
SESSION_ABSOLUTE_LIFETIME = timedelta(days=90)
SESSION_IDLE_WRITE_INTERVAL = timedelta(days=1)

# Error codes, which the frontend translates.
CODE_INVALID = "code_invalid"
EMAIL_INVALID = "email_invalid"
AGE_NOT_CONFIRMED = "age_not_confirmed"
DISPLAY_NAME_LENGTH = "display_name_length"
DISPLAY_NAME_CONTROL_CHARACTERS = "display_name_control_characters"
DISPLAY_NAME_RESERVED = "display_name_reserved"
EMAIL_UNCHANGED = "email_unchanged"
LANGUAGE_UNAVAILABLE = "language_unavailable"


@dataclass(frozen=True)
class CodeRequest:
    email: str
    language: str
    """The UI language of the sign-in page: the language of the email to an address
    without a User, and the preferred UI language of the User it registers."""
    client_ip: str
    honeypot: str = ""
    """The hidden field that people leave empty; a filled one gets the ordinary
    answer, and nothing is stored or sent."""


@dataclass(frozen=True)
class Registration:
    display_name: str
    age_confirmed: bool


@dataclass(frozen=True)
class CodeAttempt:
    email: str
    code: str
    language: str
    registration: Registration | None = None
    """The registration step's answers, sent again with the code once the address
    turned out to have no User."""


@dataclass(frozen=True)
class EmailChange:
    user_id: int
    email: str
    """The new address."""
    client_ip: str


@dataclass(frozen=True)
class RateLimited:
    wait: timedelta


@dataclass(frozen=True)
class SignedIn:
    session_token: str


@dataclass(frozen=True)
class RegistrationRequired:
    """The code is right and the address may register: ask for the registration
    step. The code is not used up."""


@dataclass(frozen=True)
class Refused:
    code: str
    """One of the error codes above."""


class Authentication(Protocol):
    async def request_code(
        self, request: CodeRequest, now: datetime
    ) -> RateLimited | Refused | None:
        """Send a code, or the email the address gets instead, or nothing; the
        answer is the same for every address, apart from the rate limits."""
        ...

    async def verify_code(
        self, attempt: CodeAttempt, now: datetime
    ) -> SignedIn | RegistrationRequired | Refused: ...

    async def passkey_registration_options(self, user_id: int, now: datetime) -> dict[str, Any]:
        """The WebAuthn options for the browser to create a passkey for the User."""
        ...

    async def register_passkey(
        self, user_id: int, name: str, credential: dict[str, Any], now: datetime
    ) -> Passkey | Refused:
        """Add the passkey the browser created from those options."""
        ...

    async def passkey_sign_in_options(self, now: datetime) -> dict[str, Any]:
        """The WebAuthn options for the browser to sign in with a passkey."""
        ...

    async def sign_in_with_passkey(
        self, credential: dict[str, Any], now: datetime
    ) -> SignedIn | Refused: ...

    async def request_email_change(
        self, request: EmailChange, now: datetime
    ) -> RateLimited | Refused | None:
        """Send a code to the new address, or Address already in use if another User
        has it; the answer is the same either way, apart from the rate limits."""
        ...

    async def confirm_email_change(self, user_id: int, code: str, now: datetime) -> Refused | None:
        """Change the address once the code sent to it is entered, and tell the old one."""
        ...
