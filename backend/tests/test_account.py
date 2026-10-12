"""Foundations spec, 2. Account and Email change: the display name (criterion 55), the
preferred UI language, and the email change (criteria 56 and 57; Notifications
criterion 36).

Through the HTTP API with a controllable clock and the emails the API deferred.
"""

import asyncio
from collections.abc import Iterator

import pytest
from auth_fixtures import BASE_URL, START, Api, open_api
from authenticator import Authenticator

from tart.db import create_engine
from tart.jobs import sweep_database


@pytest.fixture
def api(migrated_database: str) -> Iterator[Api]:
    with open_api(migrated_database) as started:
        yield started


def _change_email(api: Api, email: str):
    return api.client.post("/api/auth/account/email", json={"email": email})


def _confirm(api: Api, code: str):
    return api.client.post("/api/auth/account/email/verify", json={"code": code})


def _body(message) -> str:
    return message.get_body(("plain",)).get_content()


def _sweep(api: Api) -> None:
    async def run() -> None:
        engine = create_engine(api.dsn.replace("postgresql://", "postgresql+asyncpg://"))
        try:
            await sweep_database(engine, api.clock.now)
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_the_account_shows_the_users_settings(api: Api) -> None:
    number = api.sign_in("lettrice@example.org", "Lettrice")

    response = api.client.get("/api/auth/account")

    assert response.json() == {
        "number": number,
        "email": "lettrice@example.org",
        "display_name": "Lettrice",
        "preferred_language": "it",
    }


def test_the_account_needs_a_session(api: Api) -> None:
    assert api.client.get("/api/auth/account").json() == {"code": "sign_in_required"}
    for response in (
        api.client.patch("/api/auth/account", json={"display_name": "Nome"}),
        _change_email(api, "nuova@example.org"),
        _confirm(api, "123456"),
    ):
        assert response.status_code == 401
        assert response.json() == {"code": "sign_in_required"}


def test_criterion_55_a_new_display_name_shows_on_every_revision_past_ones_included(
    api: Api,
) -> None:
    number = api.sign_in("lettrice@example.org", "Prima firma")
    (record,) = api.query("INSERT INTO record (kind) VALUES ('site') RETURNING id")
    for submission in (1, 2):
        api.query(
            "INSERT INTO revision (record_id, submission_id, submitter_id, moderator_id, "
            "submitted_at, approved_at, changes) VALUES ($1, $2, $3, $3, $4, $4, '[]')",
            record["id"],
            submission,
            number,
            START,
        )

    response = api.client.patch("/api/auth/account", json={"display_name": "  Seconda firma "})

    assert response.status_code == 200
    assert response.json()["display_name"] == "Seconda firma"
    assert api.client.get("/api/auth/session").json()["user"]["display_name"] == "Seconda firma"
    # A Revision keeps the submitter's User number, so `/revisions` reads the
    # current name for every entry.
    names = api.query(
        "SELECT u.display_name FROM revision r JOIN user_account u ON u.id = r.submitter_id "
        "WHERE r.record_id = $1",
        record["id"],
    )
    assert [row["display_name"] for row in names] == ["Seconda firma", "Seconda firma"]


@pytest.mark.parametrize(
    ("display_name", "error"),
    [
        ("   ", "display_name_length"),
        ("x" * 41, "display_name_length"),
        ("Nome\u0007", "display_name_control_characters"),
        ("Deleted user 12", "display_name_reserved"),
        ("utente eliminato 3", "display_name_reserved"),
    ],
)
def test_a_new_display_name_follows_the_registration_rules(
    api: Api, display_name: str, error: str
) -> None:
    api.sign_in("lettrice@example.org", "Lettrice")

    response = api.client.patch("/api/auth/account", json={"display_name": display_name})

    assert response.status_code == 400
    assert response.json() == {"code": error}
    assert api.client.get("/api/auth/account").json()["display_name"] == "Lettrice"


def test_the_preferred_language_changes_the_language_of_the_users_emails(api: Api) -> None:
    api.sign_in("lettrice@example.org")

    response = api.client.patch("/api/auth/account", json={"preferred_language": "en"})

    assert response.json()["preferred_language"] == "en"
    assert api.client.get("/api/auth/session").json()["user"]["preferred_language"] == "en"
    api.clock.advance(minutes=2)
    api.request_code("lettrice@example.org", language="it")
    (message,) = api.new_emails()
    assert message["Content-Language"] == "en"


def test_a_preferred_language_that_is_not_enabled_is_refused(api: Api) -> None:
    api.sign_in("lettrice@example.org")

    response = api.client.patch("/api/auth/account", json={"preferred_language": "fr"})

    assert response.status_code == 400
    assert response.json() == {"code": "language_unavailable"}


def test_criterion_56_an_email_change_takes_effect_only_once_the_code_is_entered(
    api: Api,
) -> None:
    api.sign_in("vecchia@example.org")
    authenticator = Authenticator()
    options = api.client.post("/api/auth/passkeys/options").json()
    credential = authenticator.create(options, BASE_URL)
    api.client.post("/api/auth/passkeys", json={"name": "Telefono", "credential": credential})
    sessions_before = api.query("SELECT id_hash FROM user_session")

    assert _change_email(api, "Nuova@Example.org ").status_code == 202

    # Not yet: the address is the old one until the code is entered.
    assert api.client.get("/api/auth/account").json()["email"] == "vecchia@example.org"
    (code_email,) = api.new_emails()
    assert code_email["To"] == "nuova@example.org"
    assert "Codice per confermare il nuovo indirizzo email" in code_email["Subject"]
    assert code_email["Content-Language"] == "it"
    code = api.code_from(code_email)

    response = _confirm(api, code)

    assert response.status_code == 200
    assert response.json()["email"] == "nuova@example.org"
    (notice,) = api.new_emails()
    assert notice["To"] == "vecchia@example.org"
    assert notice["Content-Language"] == "it"
    assert "L'indirizzo email del tuo account è cambiato" in notice["Subject"]
    body = _body(notice)
    assert "n***@e***.org" in body
    assert "nuova@example.org" not in body
    assert "privacy@" in body
    # Sessions and passkeys are unchanged.
    assert api.query("SELECT id_hash FROM user_session") == sessions_before
    assert api.client.get("/api/auth/session").json()["user"] is not None
    assert len(api.client.get("/api/auth/passkeys").json()) == 1
    # The new address signs in; the old one no longer reaches the account.
    assert api.client.post("/api/auth/sign-out").status_code == 204
    api.client.cookies.clear()
    api.clock.advance(minutes=2)
    api.sign_in("nuova@example.org")
    assert api.client.get("/api/auth/account").json()["email"] == "nuova@example.org"


def test_notifications_criterion_36_the_change_emails_are_in_the_users_preferred_language(
    api: Api,
) -> None:
    api.sign_in("vecchia@example.org")
    api.client.patch("/api/auth/account", json={"preferred_language": "en"})

    _change_email(api, "nuova@example.org")
    (code_email,) = api.new_emails()
    _confirm(api, api.code_from(code_email))
    (notice,) = api.new_emails()

    assert code_email["Content-Language"] == "en"
    assert "Code to confirm your new email address" in code_email["Subject"]
    assert notice["Content-Language"] == "en"
    assert "Your email address has been changed" in notice["Subject"]


def test_criterion_57_an_address_in_use_answers_as_a_free_one_and_gets_no_code(
    api: Api,
) -> None:
    api.add_user("presa@example.org", language="en")
    api.sign_in("vecchia@example.org")

    free = _change_email(api, "libera@example.org")
    api.new_emails()
    api.clock.advance(minutes=2)
    taken = _change_email(api, "presa@example.org")

    assert (taken.status_code, taken.json()) == (free.status_code, free.json()) == (202, {})
    (message,) = api.new_emails()
    assert message["To"] == "presa@example.org"
    # The address belongs to a registered User: their preferred UI language.
    assert message["Content-Language"] == "en"
    assert "This address already has an account" in message["Subject"]
    assert not any(line.strip().isdigit() for line in _body(message).splitlines())
    # No code was issued, and the pending change to the free address ended.
    assert api.query("SELECT * FROM email_change_code") == []
    assert _confirm(api, "123456").json() == {"code": "code_invalid"}
    assert api.client.get("/api/auth/account").json()["email"] == "vecchia@example.org"


def test_an_email_change_code_follows_the_sign_in_codes_rules(api: Api) -> None:
    api.sign_in("vecchia@example.org")
    _change_email(api, "nuova@example.org")
    code = api.code_from(api.new_emails()[0])
    wrong = "000000" if code != "000000" else "111111"

    for _ in range(4):
        assert _confirm(api, wrong).json() == {"code": "code_invalid"}
    assert _confirm(api, code).status_code == 200
    api.new_emails()  # Email changed

    api.clock.advance(minutes=2)
    _change_email(api, "terza@example.org")
    code = api.code_from(api.new_emails()[0])
    for _ in range(5):
        _confirm(api, wrong)
    assert _confirm(api, code).json() == {"code": "code_invalid"}

    api.clock.advance(minutes=2)
    _change_email(api, "quarta@example.org")
    code = api.code_from(api.new_emails()[0])
    api.clock.advance(minutes=10)
    assert _confirm(api, code).json() == {"code": "code_invalid"}
    assert api.client.get("/api/auth/account").json()["email"] == "nuova@example.org"


def test_a_new_email_change_request_invalidates_the_previous_code(api: Api) -> None:
    api.sign_in("vecchia@example.org")
    _change_email(api, "prima@example.org")
    first = api.code_from(api.new_emails()[0])
    api.clock.advance(minutes=2)
    _change_email(api, "seconda@example.org")
    second = api.code_from(api.new_emails()[0])

    if first != second:
        assert _confirm(api, first).json() == {"code": "code_invalid"}
    assert _confirm(api, second).json()["email"] == "seconda@example.org"


def test_an_email_change_counts_against_the_sign_in_codes_limits(api: Api) -> None:
    api.sign_in("vecchia@example.org")
    api.request_code("nuova@example.org")

    response = _change_email(api, "nuova@example.org")

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    assert int(response.headers["Retry-After"]) > 0


def test_an_email_change_to_the_current_or_an_invalid_address_is_refused(api: Api) -> None:
    api.sign_in("vecchia@example.org")

    assert _change_email(api, " Vecchia@example.org").json() == {"code": "email_unchanged"}
    assert _change_email(api, "non-un-indirizzo").json() == {"code": "email_invalid"}
    assert api.new_emails() == []


def test_an_address_registered_after_the_code_was_sent_is_not_taken(api: Api) -> None:
    api.sign_in("vecchia@example.org")
    _change_email(api, "nuova@example.org")
    code = api.code_from(api.new_emails()[0])
    api.add_user("nuova@example.org")

    assert _confirm(api, code).json() == {"code": "code_invalid"}
    assert api.client.get("/api/auth/account").json()["email"] == "vecchia@example.org"
    assert api.new_emails() == []


def test_the_sweep_deletes_expired_email_change_codes(api: Api) -> None:
    api.sign_in("vecchia@example.org")
    _change_email(api, "nuova@example.org")
    api.clock.advance(minutes=10)

    _sweep(api)

    assert api.query("SELECT * FROM email_change_code") == []


def test_email_change_codes_are_stored_only_as_keyed_hashes(api: Api) -> None:
    api.sign_in("vecchia@example.org")
    _change_email(api, "nuova@example.org")
    code = api.code_from(api.new_emails()[0])

    (row,) = api.query("SELECT code_hash FROM email_change_code")

    assert code.encode() not in bytes(row["code_hash"])
    assert len(row["code_hash"]) == 32
