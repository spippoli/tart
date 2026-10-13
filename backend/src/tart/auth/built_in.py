"""The built-in authentication: a one-time code by email, and passkeys
(`tart.auth.passkeys`) once signed in (Foundations spec, 2. Sign-in).

The code request answers the same whatever the address, in every `registration`
mode, so that nobody learns which addresses have accounts: a User or an address
that may register gets a code, one that may not gets a "registration is not open"
email instead, and a suspended User's gets nothing. All of them count against the
same limits. An email change follows the same rules (Foundations spec, 2. Email
change): the code goes to the new address, or Address already in use if another
User has it, with the same answer. Emails are deferred to the `worker` once the
transaction is committed.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from procrastinate import App
from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as upsert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from tart import rate_limits
from tart.auth import (
    AGE_NOT_CONFIRMED,
    CODE_INVALID,
    CODE_LIFETIME,
    CODE_WRONG_ATTEMPTS,
    EMAIL_INVALID,
    EMAIL_UNCHANGED,
    CodeAttempt,
    CodeRequest,
    EmailChange,
    RateLimited,
    Refused,
    RegistrationRequired,
    SignedIn,
    passkeys,
    sessions,
)
from tart.auth.passkeys import PASSKEY_INVALID, Passkey, RelyingParty
from tart.auth.tables import email_change_code, sign_in_code, user_account
from tart.auth.tokens import keyed_hash, new_code, same
from tart.auth.users import display_name_problem, mask_email, normalise_email
from tart.jobs import SEND_EMAIL
from tart.messages import Catalogue
from tart.rate_limits import Limit

logger = logging.getLogger(__name__)

# Platform constants (Foundations spec, Instance configuration).
CODE_PER_EMAIL_MINUTE = Limit("code_per_email_minute", 1, timedelta(seconds=60))
CODE_PER_EMAIL_HOUR = Limit("code_per_email_hour", 5, timedelta(hours=1))
CODE_PER_EMAIL_DAY = Limit("code_per_email_day", 10, timedelta(hours=24))
CODE_PER_IP_HOUR = Limit("code_per_ip_hour", 20, timedelta(hours=1))

SIGN_IN_CODE_EMAIL = "sign_in_code"
REGISTRATION_NOT_OPEN_EMAIL = "registration_not_open"
NEW_ADDRESS_CODE_EMAIL = "new_address_code"
ADDRESS_IN_USE_EMAIL = "address_in_use"
EMAIL_CHANGED_EMAIL = "email_changed"


@dataclass(frozen=True)
class _Email:
    kind: str
    to: str
    language: str
    params: dict[str, object]


@dataclass(frozen=True)
class BuiltInAuthentication:
    engine: AsyncEngine
    jobs: App
    key: bytes
    """`SESSION_KEY`, for the keyed hashes of codes, sessions, and rate-limit keys."""
    registration: str
    """`community.registration`: `open`, `invite`, or `closed`."""
    ui_languages: Sequence[str]
    catalogue: Catalogue
    relying_party: RelyingParty
    privacy_contact: str
    """`contacts.privacy`, where the Email changed notice says to contest a change."""

    def _may_register(self, email: str) -> bool:
        # Under `invite`, the Invitations ticket admits an address with a pending
        # Invitation; until then no address may register.
        return self.registration == "open"

    def _language(self, requested: str) -> str:
        return requested if requested in self.ui_languages else self.ui_languages[0]

    def _code_hash(self, email: str, code: str) -> bytes:
        return keyed_hash(self.key, "sign-in code", email, code)

    async def _defer(self, message: _Email) -> None:
        await self.jobs.configure_task(SEND_EMAIL).defer_async(
            kind=message.kind, to=message.to, language=message.language, params=message.params
        )

    async def _hit_code_limits(
        self, connection: AsyncConnection, email: str, client_ip: str, now: datetime
    ) -> timedelta | None:
        return await rate_limits.hit(
            connection,
            [
                (CODE_PER_EMAIL_MINUTE, email),
                (CODE_PER_EMAIL_HOUR, email),
                (CODE_PER_EMAIL_DAY, email),
                (CODE_PER_IP_HOUR, client_ip),
            ],
            now,
            self.key,
        )

    async def request_code(
        self, request: CodeRequest, now: datetime
    ) -> RateLimited | Refused | None:
        if request.honeypot:
            return None
        email = normalise_email(request.email)
        if email is None:
            return Refused(EMAIL_INVALID)
        language = self._language(request.language)
        message: _Email | None = None
        async with self.engine.begin() as connection:
            wait = await self._hit_code_limits(connection, email, request.client_ip, now)
            if wait is not None:
                return RateLimited(wait)
            user = (
                await connection.execute(
                    select(user_account.c.preferred_language, user_account.c.suspended_at).where(
                        user_account.c.email == email
                    )
                )
            ).one_or_none()
            if user is not None and user.suspended_at is not None:
                pass
            elif user is not None or self._may_register(email):
                code = new_code()
                values = {
                    "code_hash": self._code_hash(email, code),
                    "expires_at": now + CODE_LIFETIME,
                    "wrong_attempts": 0,
                }
                # Replacing the row invalidates the previous code.
                await connection.execute(
                    upsert(sign_in_code)
                    .values(email=email, **values)
                    .on_conflict_do_update(index_elements=[sign_in_code.c.email], set_=values)
                )
                message = _Email(
                    SIGN_IN_CODE_EMAIL,
                    email,
                    user.preferred_language if user is not None else language,
                    {"code": code, "minutes": int(CODE_LIFETIME.total_seconds() // 60)},
                )
            else:
                message = _Email(REGISTRATION_NOT_OPEN_EMAIL, email, language, {})
        if message is not None:
            await self._defer(message)
        return None

    async def verify_code(
        self, attempt: CodeAttempt, now: datetime
    ) -> SignedIn | RegistrationRequired | Refused:
        email = normalise_email(attempt.email)
        if email is None:
            return Refused(CODE_INVALID)
        async with self.engine.begin() as connection:
            row = (
                await connection.execute(
                    select(sign_in_code).where(sign_in_code.c.email == email).with_for_update()
                )
            ).one_or_none()
            if row is None:
                return Refused(CODE_INVALID)
            used_up = delete(sign_in_code).where(sign_in_code.c.email == email)
            if row.expires_at <= now:
                await connection.execute(used_up)
                return Refused(CODE_INVALID)
            if not same(self._code_hash(email, attempt.code.strip()), row.code_hash):
                if row.wrong_attempts + 1 >= CODE_WRONG_ATTEMPTS:
                    await connection.execute(used_up)
                else:
                    await connection.execute(
                        update(sign_in_code)
                        .where(sign_in_code.c.email == email)
                        .values(wrong_attempts=row.wrong_attempts + 1)
                    )
                return Refused(CODE_INVALID)

            user = (
                await connection.execute(
                    select(user_account.c.id, user_account.c.suspended_at).where(
                        user_account.c.email == email
                    )
                )
            ).one_or_none()
            if user is not None:
                await connection.execute(used_up)
                if user.suspended_at is not None:
                    return Refused(CODE_INVALID)
                logger.info("signed in with a code", extra={"user_id": user.id})
                return SignedIn(await sessions.create(connection, user.id, now, self.key))
            if not self._may_register(email):
                await connection.execute(used_up)
                return Refused(CODE_INVALID)
            registration = attempt.registration
            if registration is None:
                return RegistrationRequired()
            if not registration.age_confirmed:
                return Refused(AGE_NOT_CONFIRMED)
            problem = display_name_problem(
                registration.display_name, self.catalogue, self.ui_languages
            )
            if problem is not None:
                return Refused(problem)
            user_id = await connection.scalar(
                insert(user_account)
                .values(
                    email=email,
                    display_name=registration.display_name.strip(),
                    preferred_language=self._language(attempt.language),
                    created_at=now,
                )
                .returning(user_account.c.id)
            )
            await connection.execute(used_up)
            logger.info("registered and signed in", extra={"user_id": user_id})
            return SignedIn(await sessions.create(connection, user_id, now, self.key))

    async def passkey_registration_options(self, user_id: int, now: datetime) -> dict[str, Any]:
        async with self.engine.begin() as connection:
            return await passkeys.registration_options(
                connection, self.relying_party, user_id, now, self.key
            )

    async def register_passkey(
        self, user_id: int, name: str, credential: dict[str, Any], now: datetime
    ) -> Passkey | Refused:
        async with self.engine.begin() as connection:
            outcome = await passkeys.register(
                connection, self.relying_party, user_id, name, credential, now, self.key
            )
        return Refused(outcome) if isinstance(outcome, str) else outcome

    async def passkey_sign_in_options(self, now: datetime) -> dict[str, Any]:
        async with self.engine.begin() as connection:
            return await passkeys.sign_in_options(connection, self.relying_party, now, self.key)

    async def sign_in_with_passkey(
        self, credential: dict[str, Any], now: datetime
    ) -> SignedIn | Refused:
        async with self.engine.begin() as connection:
            user_id = await passkeys.authenticate(
                connection, self.relying_party, credential, now, self.key
            )
            if user_id is None:
                return Refused(PASSKEY_INVALID)
            logger.info("signed in with a passkey", extra={"user_id": user_id})
            return SignedIn(await sessions.create(connection, user_id, now, self.key))

    def _change_code_hash(self, user_id: int, email: str, code: str) -> bytes:
        return keyed_hash(self.key, "email change code", str(user_id), email, code)

    async def request_email_change(
        self, request: EmailChange, now: datetime
    ) -> RateLimited | Refused | None:
        email = normalise_email(request.email)
        if email is None:
            return Refused(EMAIL_INVALID)
        async with self.engine.begin() as connection:
            user = (
                await connection.execute(
                    select(user_account.c.email, user_account.c.preferred_language).where(
                        user_account.c.id == request.user_id
                    )
                )
            ).one()
            if email == user.email:
                return Refused(EMAIL_UNCHANGED)
            wait = await self._hit_code_limits(connection, email, request.client_ip, now)
            if wait is not None:
                return RateLimited(wait)
            holder = (
                await connection.execute(
                    select(user_account.c.preferred_language).where(user_account.c.email == email)
                )
            ).one_or_none()
            pending = email_change_code.c.user_id == request.user_id
            if holder is not None:
                # No code: a pending change to another address ends too, as a new
                # request for a free address would end it.
                await connection.execute(delete(email_change_code).where(pending))
                message = _Email(ADDRESS_IN_USE_EMAIL, email, holder.preferred_language, {})
            else:
                code = new_code()
                values = {
                    "new_email": email,
                    "code_hash": self._change_code_hash(request.user_id, email, code),
                    "expires_at": now + CODE_LIFETIME,
                    "wrong_attempts": 0,
                }
                await connection.execute(
                    upsert(email_change_code)
                    .values(user_id=request.user_id, **values)
                    .on_conflict_do_update(
                        index_elements=[email_change_code.c.user_id], set_=values
                    )
                )
                message = _Email(
                    NEW_ADDRESS_CODE_EMAIL,
                    email,
                    user.preferred_language,
                    {"code": code, "minutes": int(CODE_LIFETIME.total_seconds() // 60)},
                )
        await self._defer(message)
        return None

    async def confirm_email_change(self, user_id: int, code: str, now: datetime) -> Refused | None:
        async with self.engine.begin() as connection:
            pending = email_change_code.c.user_id == user_id
            row = (
                await connection.execute(select(email_change_code).where(pending).with_for_update())
            ).one_or_none()
            if row is None:
                return Refused(CODE_INVALID)
            used_up = delete(email_change_code).where(pending)
            if row.expires_at <= now:
                await connection.execute(used_up)
                return Refused(CODE_INVALID)
            if not same(
                self._change_code_hash(user_id, row.new_email, code.strip()), row.code_hash
            ):
                if row.wrong_attempts + 1 >= CODE_WRONG_ATTEMPTS:
                    await connection.execute(used_up)
                else:
                    await connection.execute(
                        update(email_change_code)
                        .where(pending)
                        .values(wrong_attempts=row.wrong_attempts + 1)
                    )
                return Refused(CODE_INVALID)
            await connection.execute(used_up)
            user = (
                await connection.execute(
                    select(user_account.c.email, user_account.c.preferred_language).where(
                        user_account.c.id == user_id
                    )
                )
            ).one()
            try:
                async with connection.begin_nested():
                    await connection.execute(
                        update(user_account)
                        .where(user_account.c.id == user_id)
                        .values(email=row.new_email)
                    )
            except IntegrityError:
                # Someone registered the address after the code was sent.
                return Refused(CODE_INVALID)
        await self._defer(
            _Email(
                EMAIL_CHANGED_EMAIL,
                user.email,
                user.preferred_language,
                {
                    "masked_email": mask_email(row.new_email),
                    "privacy_contact": self.privacy_contact,
                },
            )
        )
        return None
