"""Foundations spec, 2. Sign-in: passkeys, added and removed by the signed-in User and
used to sign in (criterion 12), refused once the User is suspended (criterion 52).

Through the HTTP API with a controllable clock and a software authenticator that
answers the API's WebAuthn options as a browser would.
"""

import asyncio
from collections.abc import Iterator
from typing import Any

import pytest
from auth_fixtures import BASE_URL, Api, open_api
from authenticator import Authenticator

from tart.auth.sessions import COOKIE
from tart.cli import main as run_cli
from tart.db import create_engine
from tart.jobs import sweep_database


@pytest.fixture
def api(migrated_database: str) -> Iterator[Api]:
    with open_api(migrated_database) as started:
        yield started


def _options(api: Api, path: str) -> dict[str, Any]:
    response = api.client.post(path)
    assert response.status_code == 200, response.text
    return response.json()


def _add(api: Api, authenticator: Authenticator, name: str = "Telefono") -> Any:
    credential = authenticator.create(_options(api, "/api/auth/passkeys/options"), BASE_URL)
    return api.client.post("/api/auth/passkeys", json={"name": name, "credential": credential})


def _sign_in(api: Api, authenticator: Authenticator, origin: str = BASE_URL) -> Any:
    credential = authenticator.get(_options(api, "/api/auth/passkey/options"), origin)
    return api.client.post("/api/auth/passkey/verify", json={"credential": credential})


def _sign_out(api: Api) -> None:
    assert api.client.post("/api/auth/sign-out").status_code == 204
    api.client.cookies.clear()


def _session(api: Api) -> dict:
    return api.client.get("/api/auth/session").json()


# Criterion 12.


def test_criterion_12_a_user_adds_a_passkey_and_then_signs_in_with_it(api: Api) -> None:
    user = api.sign_in("persona@example.org")
    authenticator = Authenticator()

    added = _add(api, authenticator, " Telefono di Persona ")

    assert added.status_code == 201, added.text
    assert added.json()["name"] == "Telefono di Persona"
    _sign_out(api)
    assert _session(api) == {"user": None}

    response = _sign_in(api, authenticator)

    assert response.json() == {"outcome": "signed_in"}
    assert COOKIE in response.cookies
    assert _session(api)["user"]["number"] == user


def test_passkey_options_bind_to_the_site_and_ask_for_a_discoverable_verified_passkey(
    api: Api,
) -> None:
    api.sign_in("persona@example.org", display_name="Persona")

    options = _options(api, "/api/auth/passkeys/options")

    assert options["rp"] == {
        "id": "archive.example.org",
        "name": "Archivio di prova dell'arte urbana",
    }
    assert options["user"]["name"] == "persona@example.org"
    assert options["user"]["displayName"] == "Persona"
    assert options["authenticatorSelection"]["residentKey"] == "required"
    assert options["authenticatorSelection"]["userVerification"] == "required"
    assert options["timeout"] == 300000
    sign_in = _options(api, "/api/auth/passkey/options")
    assert sign_in["rpId"] == "archive.example.org"
    assert sign_in["userVerification"] == "required"
    assert sign_in["allowCredentials"] == []


def test_the_options_exclude_the_users_existing_passkeys(api: Api) -> None:
    api.sign_in("persona@example.org")
    authenticator = Authenticator()
    first = authenticator.create(_options(api, "/api/auth/passkeys/options"), BASE_URL)
    api.client.post("/api/auth/passkeys", json={"name": "Telefono", "credential": first})

    options = _options(api, "/api/auth/passkeys/options")

    assert [entry["id"] for entry in options["excludeCredentials"]] == [first["id"]]
    assert options["excludeCredentials"][0]["transports"] == ["internal", "hybrid"]


def test_the_account_lists_passkeys_by_name_and_date_without_key_material(api: Api) -> None:
    api.sign_in("persona@example.org")
    _add(api, Authenticator(), "Telefono")
    api.clock.advance(days=1)
    _add(api, Authenticator(), "Chiave USB")

    listed = api.client.get("/api/auth/passkeys").json()

    assert [(entry["name"], entry["created_at"]) for entry in listed] == [
        ("Telefono", "2026-10-01T09:00:00Z"),
        ("Chiave USB", "2026-10-02T09:00:00Z"),
    ]
    assert set(listed[0]) == {"id", "name", "created_at"}


def test_a_removed_passkey_no_longer_signs_in(api: Api) -> None:
    api.sign_in("persona@example.org")
    authenticator = Authenticator()
    passkey_id = _add(api, authenticator).json()["id"]

    assert api.client.delete(f"/api/auth/passkeys/{passkey_id}").status_code == 204

    assert api.client.get("/api/auth/passkeys").json() == []
    _sign_out(api)
    response = _sign_in(api, authenticator)
    assert (response.status_code, response.json()) == (400, {"code": "passkey_invalid"})


def test_a_user_cannot_see_or_remove_another_users_passkey(api: Api) -> None:
    api.sign_in("persona@example.org")
    passkey_id = _add(api, Authenticator()).json()["id"]
    _sign_out(api)
    api.sign_in("altra@example.org")

    assert api.client.get("/api/auth/passkeys").json() == []
    response = api.client.delete(f"/api/auth/passkeys/{passkey_id}")
    assert (response.status_code, response.json()) == (404, {"code": "passkey_not_found"})
    assert len(api.query("SELECT id FROM passkey")) == 1


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/auth/passkeys"),
        ("POST", "/api/auth/passkeys/options"),
        ("DELETE", "/api/auth/passkeys/1"),
    ],
)
def test_managing_passkeys_needs_a_session(api: Api, method: str, path: str) -> None:
    response = api.client.request(method, path)

    assert (response.status_code, response.json()) == (401, {"code": "sign_in_required"})


def test_adding_a_passkey_needs_a_session(api: Api) -> None:
    response = api.client.post("/api/auth/passkeys", json={"name": "Telefono", "credential": {}})

    assert (response.status_code, response.json()) == (401, {"code": "sign_in_required"})


@pytest.mark.parametrize(
    ("name", "error"),
    [
        ("   ", "passkey_name_length"),
        ("x" * 41, "passkey_name_length"),
        ("Tele\tfono", "passkey_name_control_characters"),
    ],
)
def test_passkey_name_rules(api: Api, name: str, error: str) -> None:
    api.sign_in("persona@example.org")

    response = _add(api, Authenticator(), name)

    assert (response.status_code, response.json()) == (400, {"code": error})


def test_a_passkey_name_of_40_characters_is_accepted(api: Api) -> None:
    api.sign_in("persona@example.org")

    assert _add(api, Authenticator(), "x" * 40).status_code == 201


def test_a_passkey_without_user_verification_is_refused(api: Api) -> None:
    api.sign_in("persona@example.org")

    response = _add(api, Authenticator(verifies_user=False))

    assert (response.status_code, response.json()) == (400, {"code": "passkey_invalid"})


def test_signing_in_without_user_verification_is_refused(api: Api) -> None:
    api.sign_in("persona@example.org")
    authenticator = Authenticator()
    _add(api, authenticator)
    _sign_out(api)

    authenticator.verifies_user = False
    response = _sign_in(api, authenticator)

    assert (response.status_code, response.json()) == (400, {"code": "passkey_invalid"})


def test_a_passkey_response_for_another_site_is_refused(api: Api) -> None:
    api.sign_in("persona@example.org")
    authenticator = Authenticator()
    _add(api, authenticator)
    _sign_out(api)

    response = _sign_in(api, authenticator, origin="https://evil.example")

    assert (response.status_code, response.json()) == (400, {"code": "passkey_invalid"})
    assert _session(api) == {"user": None}


def test_a_challenge_serves_once(api: Api) -> None:
    api.sign_in("persona@example.org")
    authenticator = Authenticator()
    _add(api, authenticator)
    _sign_out(api)
    credential = authenticator.get(_options(api, "/api/auth/passkey/options"), BASE_URL)
    first = api.client.post("/api/auth/passkey/verify", json={"credential": credential})
    assert first.json() == {"outcome": "signed_in"}
    _sign_out(api)

    replayed = api.client.post("/api/auth/passkey/verify", json={"credential": credential})

    assert (replayed.status_code, replayed.json()) == (400, {"code": "passkey_invalid"})


def test_a_challenge_expires_after_5_minutes(api: Api) -> None:
    api.sign_in("persona@example.org")
    authenticator = Authenticator()
    _add(api, authenticator)
    _sign_out(api)
    credential = authenticator.get(_options(api, "/api/auth/passkey/options"), BASE_URL)

    api.clock.advance(minutes=5)

    response = api.client.post("/api/auth/passkey/verify", json={"credential": credential})
    assert (response.status_code, response.json()) == (400, {"code": "passkey_invalid"})


def test_a_challenge_issued_to_one_user_cannot_add_a_passkey_to_another(api: Api) -> None:
    api.sign_in("persona@example.org")
    credential = Authenticator().create(_options(api, "/api/auth/passkeys/options"), BASE_URL)
    _sign_out(api)
    api.sign_in("altra@example.org")

    response = api.client.post(
        "/api/auth/passkeys", json={"name": "Telefono", "credential": credential}
    )

    assert (response.status_code, response.json()) == (400, {"code": "passkey_invalid"})


def test_a_sign_in_challenge_cannot_add_a_passkey(api: Api) -> None:
    api.sign_in("persona@example.org")
    options = _options(api, "/api/auth/passkeys/options")
    options["challenge"] = _options(api, "/api/auth/passkey/options")["challenge"]
    credential = Authenticator().create(options, BASE_URL)

    response = api.client.post(
        "/api/auth/passkeys", json={"name": "Telefono", "credential": credential}
    )

    assert (response.status_code, response.json()) == (400, {"code": "passkey_invalid"})


def test_a_malformed_credential_is_refused(api: Api) -> None:
    response = api.client.post("/api/auth/passkey/verify", json={"credential": {"id": "x"}})

    assert (response.status_code, response.json()) == (400, {"code": "passkey_invalid"})


def test_the_hourly_sweep_deletes_expired_challenges(api: Api, migrated_database: str) -> None:
    _options(api, "/api/auth/passkey/options")
    api.clock.advance(minutes=5)
    _options(api, "/api/auth/passkey/options")

    async def sweep() -> None:
        engine = create_engine(migrated_database)
        try:
            await sweep_database(engine, api.clock.now)
        finally:
            await engine.dispose()

    asyncio.run(sweep())

    assert len(api.query("SELECT challenge_hash FROM passkey_challenge")) == 1


# Criterion 52.


def test_criterion_52_a_suspended_users_passkey_is_refused_and_works_again_once_lifted(
    api: Api,
) -> None:
    api.sign_in("persona@example.org")
    authenticator = Authenticator()
    _add(api, authenticator)
    _sign_out(api)

    assert run_cli(["users", "suspend", "persona@example.org", "--reason", "Prova"]) == 0

    response = _sign_in(api, authenticator)
    assert (response.status_code, response.json()) == (400, {"code": "passkey_invalid"})
    assert _session(api) == {"user": None}

    assert run_cli(["users", "unsuspend", "persona@example.org"]) == 0

    assert _sign_in(api, authenticator).json() == {"outcome": "signed_in"}
