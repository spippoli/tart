"""Passkeys (WebAuthn) through py_webauthn (Foundations spec, 2. Sign-in; ADR 0005).

A signed-in User adds passkeys on the Account page, names them, and removes them;
anyone signs in with one without typing an address, since every passkey is a
discoverable credential. Both ceremonies ask for user verification, because a
passkey replaces the email code rather than adding to it.

Each ceremony starts with options that carry a fresh challenge, stored as a keyed
hash for five minutes and deleted when a response presents it, so that a challenge
serves once. A suspended User's passkeys are refused.
"""

import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as upsert
from sqlalchemy.ext.asyncio import AsyncConnection
from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import bytes_to_base64url, parse_client_data_json
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorTransport,
    PublicKeyCredentialCreationOptions,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialRequestOptions,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from tart.auth.tables import passkey, passkey_challenge, user_account
from tart.auth.tokens import keyed_hash

# Platform constants.
CHALLENGE_LIFETIME = timedelta(minutes=5)
NAME_MAX_LENGTH = 40

# Error codes, which the frontend translates.
PASSKEY_INVALID = "passkey_invalid"
"""A response that does not verify, an expired or used challenge, a passkey that is
not registered, or one of a suspended User: sign-in never says which."""
PASSKEY_NAME_LENGTH = "passkey_name_length"
PASSKEY_NAME_CONTROL_CHARACTERS = "passkey_name_control_characters"

_TRANSPORTS = {transport.value for transport in AuthenticatorTransport}


@dataclass(frozen=True)
class RelyingParty:
    """The site passkeys are bound to: the host and origin of `PUBLIC_BASE_URL`."""

    id: str
    name: str
    origin: str

    @classmethod
    def for_site(cls, public_base_url: str, name: str) -> RelyingParty:
        url = urlsplit(public_base_url)
        return cls(id=url.hostname or "", name=name, origin=f"{url.scheme}://{url.netloc}")


@dataclass(frozen=True)
class Passkey:
    id: int
    name: str
    created_at: datetime


def name_problem(value: str) -> str | None:
    """The error code of a passkey name, or None if it may be used as entered (trimmed)."""
    name = value.strip()
    if not 1 <= len(name) <= NAME_MAX_LENGTH:
        return PASSKEY_NAME_LENGTH
    if any(unicodedata.category(character) == "Cc" for character in name):
        return PASSKEY_NAME_CONTROL_CHARACTERS
    return None


def _challenge_hash(key: bytes, challenge: bytes) -> bytes:
    return keyed_hash(key, "passkey challenge", bytes_to_base64url(challenge))


async def _store_challenge(
    connection: AsyncConnection, challenge: bytes, user_id: int | None, now: datetime, key: bytes
) -> None:
    await connection.execute(
        insert(passkey_challenge).values(
            challenge_hash=_challenge_hash(key, challenge),
            user_id=user_id,
            expires_at=now + CHALLENGE_LIFETIME,
        )
    )


async def _take_challenge(
    connection: AsyncConnection, credential: dict[str, Any], now: datetime, key: bytes
) -> tuple[bytes, int | None] | None:
    """The challenge the response signed and the User it was issued to, if it is live;
    the challenge is used up either way."""
    try:
        client_data = base64url_to_bytes(credential["response"]["clientDataJSON"])
        challenge = parse_client_data_json(client_data).challenge
    except KeyError, TypeError, ValueError, WebAuthnException:
        return None
    row = (
        await connection.execute(
            delete(passkey_challenge)
            .where(passkey_challenge.c.challenge_hash == _challenge_hash(key, challenge))
            .returning(passkey_challenge.c.user_id, passkey_challenge.c.expires_at)
        )
    ).one_or_none()
    if row is None or row.expires_at <= now:
        return None
    return challenge, row.user_id


async def registration_options(
    connection: AsyncConnection, party: RelyingParty, user_id: int, now: datetime, key: bytes
) -> dict[str, Any]:
    """The options for the browser to create a passkey for the User, in WebAuthn's
    JSON form; the User's own passkeys are excluded."""
    user = (
        await connection.execute(
            select(user_account.c.email, user_account.c.display_name).where(
                user_account.c.id == user_id
            )
        )
    ).one()
    existing = await connection.execute(
        select(passkey.c.credential_id, passkey.c.transports).where(passkey.c.user_id == user_id)
    )
    options = generate_registration_options(
        rp_id=party.id,
        rp_name=party.name,
        user_name=user.email,
        user_id=user_id.to_bytes(8),
        user_display_name=user.display_name,
        timeout=int(CHALLENGE_LIFETIME.total_seconds() * 1000),
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(
                id=row.credential_id,
                transports=[AuthenticatorTransport(value) for value in row.transports],
            )
            for row in existing
        ],
    )
    await _store_challenge(connection, options.challenge, user_id, now, key)
    return _as_json(options)


async def register(
    connection: AsyncConnection,
    party: RelyingParty,
    user_id: int,
    name: str,
    credential: dict[str, Any],
    now: datetime,
    key: bytes,
) -> Passkey | str:
    """Add the passkey the browser created; an error code if it cannot be added."""
    problem = name_problem(name)
    if problem is not None:
        return problem
    taken = await _take_challenge(connection, credential, now, key)
    if taken is None or taken[1] != user_id:
        return PASSKEY_INVALID
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=taken[0],
            expected_rp_id=party.id,
            expected_origin=party.origin,
            require_user_verification=True,
        )
    except WebAuthnException:
        return PASSKEY_INVALID
    transports = credential["response"].get("transports")
    if not isinstance(transports, list):
        transports = []
    name = name.strip()
    passkey_id = await connection.scalar(
        upsert(passkey)
        .values(
            user_id=user_id,
            credential_id=verified.credential_id,
            public_key=verified.credential_public_key,
            sign_count=verified.sign_count,
            transports=[value for value in transports if value in _TRANSPORTS],
            name=name,
            created_at=now,
        )
        # The same authenticator registered twice: keep the first.
        .on_conflict_do_nothing(index_elements=[passkey.c.credential_id])
        .returning(passkey.c.id)
    )
    if passkey_id is None:
        return PASSKEY_INVALID
    return Passkey(passkey_id, name, now)


async def sign_in_options(
    connection: AsyncConnection, party: RelyingParty, now: datetime, key: bytes
) -> dict[str, Any]:
    """The options for the browser to sign in with any passkey of this site."""
    options = generate_authentication_options(
        rp_id=party.id,
        timeout=int(CHALLENGE_LIFETIME.total_seconds() * 1000),
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    await _store_challenge(connection, options.challenge, None, now, key)
    return _as_json(options)


async def authenticate(
    connection: AsyncConnection,
    party: RelyingParty,
    credential: dict[str, Any],
    now: datetime,
    key: bytes,
) -> int | None:
    """The User the passkey signs in, or None."""
    taken = await _take_challenge(connection, credential, now, key)
    if taken is None or taken[1] is not None:
        return None
    try:
        credential_id = base64url_to_bytes(credential["rawId"])
    except KeyError, TypeError, ValueError:
        return None
    row = (
        await connection.execute(
            select(passkey.c.id, passkey.c.user_id, passkey.c.public_key, passkey.c.sign_count)
            .join(user_account, user_account.c.id == passkey.c.user_id)
            .where(passkey.c.credential_id == credential_id, user_account.c.suspended_at.is_(None))
        )
    ).one_or_none()
    if row is None:
        return None
    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=taken[0],
            expected_rp_id=party.id,
            expected_origin=party.origin,
            credential_public_key=row.public_key,
            credential_current_sign_count=row.sign_count,
            require_user_verification=True,
        )
    except WebAuthnException:
        return None
    await connection.execute(
        update(passkey).where(passkey.c.id == row.id).values(sign_count=verified.new_sign_count)
    )
    return row.user_id


async def list_for(connection: AsyncConnection, user_id: int) -> list[Passkey]:
    rows = await connection.execute(
        select(passkey.c.id, passkey.c.name, passkey.c.created_at)
        .where(passkey.c.user_id == user_id)
        .order_by(passkey.c.created_at, passkey.c.id)
    )
    return [Passkey(row.id, row.name, row.created_at) for row in rows]


async def remove(connection: AsyncConnection, user_id: int, passkey_id: int) -> bool:
    """Remove one of the User's passkeys; False if they have none with that id."""
    result = await connection.execute(
        delete(passkey).where(passkey.c.id == passkey_id, passkey.c.user_id == user_id)
    )
    return result.rowcount == 1


async def delete_expired_challenges(connection: AsyncConnection, now: datetime) -> None:
    """Delete the challenges past their lifetime (the hourly sweep)."""
    await connection.execute(delete(passkey_challenge).where(passkey_challenge.c.expires_at <= now))


def _as_json(
    options: PublicKeyCredentialCreationOptions | PublicKeyCredentialRequestOptions,
) -> dict[str, Any]:
    return json.loads(options_to_json(options))
