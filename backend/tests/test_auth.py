"""Foundations spec, 2. Authentication and sessions: sign-in by email code,
registration, sessions, CSRF, rate limits, and the neutral answer.

Through the HTTP API with a controllable clock; the emails are the jobs the API
deferred, rendered as the worker would through the capturing email adapter.
"""

import asyncio
import re
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from auth_fixtures import BASE_URL, Api, instance_with, open_api
from fastapi.testclient import TestClient

from tart.auth.sessions import COOKIE
from tart.db import create_engine
from tart.jobs import sweep_database

REGISTRATION = {"display_name": "Lettrice di prova", "age_confirmed": True}


@pytest.fixture
def api(migrated_database: str) -> Iterator[Api]:
    with open_api(migrated_database) as started:
        yield started


def _code(api: Api, email: str, language: str = "it") -> str:
    assert api.request_code(email, language).status_code == 202
    (message,) = api.new_emails()
    return api.code_from(message)


# Criterion 10, 46: the code.


def test_criterion_10_a_code_request_emails_a_six_digit_code_that_signs_in(api: Api) -> None:
    api.add_user("persona@example.org")

    response = api.request_code("Persona@Example.org ")

    assert response.status_code == 202
    (message,) = api.new_emails()
    assert message["To"] == "persona@example.org"
    assert message["Subject"] == "[Archivio di prova dell'arte urbana] Il tuo codice di accesso"
    code = api.code_from(message)
    assert len(code) == 6 and code.isdigit()
    assert api.verify("persona@example.org", code).json() == {"outcome": "signed_in"}


def test_criterion_10_a_code_is_rejected_after_10_minutes(api: Api) -> None:
    api.add_user("persona@example.org")
    code = _code(api, "persona@example.org")

    api.clock.advance(minutes=10)

    response = api.verify("persona@example.org", code)
    assert response.status_code == 400
    assert response.json() == {"code": "code_invalid"}


def test_criterion_10_a_code_just_inside_10_minutes_still_works(api: Api) -> None:
    api.add_user("persona@example.org")
    code = _code(api, "persona@example.org")

    api.clock.advance(minutes=9, seconds=59)

    assert api.verify("persona@example.org", code).json() == {"outcome": "signed_in"}


def test_criteria_10_46_a_code_is_refused_after_5_wrong_attempts_within_its_lifetime(
    api: Api,
) -> None:
    api.add_user("persona@example.org")
    code = _code(api, "persona@example.org")
    wrong = f"{(int(code) + 1) % 1_000_000:06d}"

    for _ in range(5):
        assert api.verify("persona@example.org", wrong).json() == {"code": "code_invalid"}

    assert api.verify("persona@example.org", code).json() == {"code": "code_invalid"}


def test_criterion_46_four_wrong_attempts_leave_the_code_usable(api: Api) -> None:
    api.add_user("persona@example.org")
    code = _code(api, "persona@example.org")
    wrong = f"{(int(code) + 1) % 1_000_000:06d}"

    for _ in range(4):
        api.verify("persona@example.org", wrong)

    assert api.verify("persona@example.org", code).json() == {"outcome": "signed_in"}


def test_criterion_46_a_newly_requested_code_invalidates_the_previous_one(api: Api) -> None:
    api.add_user("persona@example.org")
    first = _code(api, "persona@example.org")
    api.clock.advance(seconds=60)
    second = _code(api, "persona@example.org")

    if first != second:
        assert api.verify("persona@example.org", first).json() == {"code": "code_invalid"}
    assert api.verify("persona@example.org", second).json() == {"outcome": "signed_in"}


def test_codes_and_sessions_are_stored_only_as_keyed_hashes(api: Api) -> None:
    api.add_user("persona@example.org")
    code = _code(api, "persona@example.org")
    api.verify("persona@example.org", code)
    token = api.client.cookies[COOKIE]

    (row,) = api.query("SELECT code_hash FROM sign_in_code") or [None]
    stored = api.query("SELECT id_hash FROM user_session")

    assert row is None  # Used up.
    assert stored and all(token.encode() not in bytes(r["id_hash"]) for r in stored)


# Criteria 11, 54, 20: registration.


def test_criterion_11_under_open_a_new_address_registers_after_the_age_declaration(
    api: Api,
) -> None:
    code = _code(api, "nuova@example.org")

    asked = api.verify("nuova@example.org", code)
    assert asked.json() == {"outcome": "registration_required"}
    assert api.client.get("/api/auth/session").json() == {"user": None}

    response = api.verify("nuova@example.org", code, registration=REGISTRATION)

    # No manual approval step: the new User is signed in at once.
    assert response.json() == {"outcome": "signed_in"}
    user = api.client.get("/api/auth/session").json()["user"]
    assert user["display_name"] == "Lettrice di prova"
    assert user["moderator"] is False


def test_criteria_11_54_registration_cannot_finish_without_the_age_declaration(api: Api) -> None:
    code = _code(api, "nuova@example.org")

    response = api.verify(
        "nuova@example.org", code, registration={**REGISTRATION, "age_confirmed": False}
    )

    assert response.status_code == 400
    assert response.json() == {"code": "age_not_confirmed"}
    assert api.query("SELECT id FROM user_account") == []


def test_criterion_11_under_closed_a_new_address_cannot_register(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, migrated_database: str
) -> None:
    instance_with(tmp_path, monkeypatch, 'registration = "open"', 'registration = "closed"')
    with open_api(migrated_database) as closed:
        assert closed.request_code("nuova@example.org").status_code == 202
        (message,) = closed.new_emails()
        assert "Le registrazioni non sono aperte" in message["Subject"]

        for code in ("000000", "123456"):
            response = closed.verify("nuova@example.org", code, registration=REGISTRATION)
            assert response.json() == {"code": "code_invalid"}
        assert closed.query("SELECT id FROM user_account") == []


def test_criterion_11_under_closed_an_existing_user_still_signs_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, migrated_database: str
) -> None:
    instance_with(tmp_path, monkeypatch, 'registration = "open"', 'registration = "closed"')
    with open_api(migrated_database) as closed:
        closed.add_user("persona@example.org")
        code = _code(closed, "persona@example.org")

        assert closed.verify("persona@example.org", code).json() == {"outcome": "signed_in"}


@pytest.mark.parametrize(
    ("display_name", "error"),
    [
        ("", "display_name_length"),
        ("   ", "display_name_length"),
        ("x" * 41, "display_name_length"),
        ("Nome\u0007", "display_name_control_characters"),
        ("Deleted user 142", "display_name_reserved"),
        ("utente  eliminato 7", "display_name_reserved"),
        ("Utente eliminato 0", "display_name_reserved"),
    ],
)
def test_criterion_54_display_name_rules(api: Api, display_name: str, error: str) -> None:
    code = _code(api, "nuova@example.org")

    response = api.verify(
        "nuova@example.org", code, registration={**REGISTRATION, "display_name": display_name}
    )

    assert response.status_code == 400
    assert response.json() == {"code": error}


def test_criterion_54_a_display_name_is_trimmed_to_up_to_40_characters_and_not_unique(
    api: Api,
) -> None:
    for email in ("prima@example.org", "seconda@example.org"):
        code = _code(api, email)
        name = "  " + "Ä" * 40 + " "
        response = api.verify(email, code, registration={**REGISTRATION, "display_name": name})
        assert response.json() == {"outcome": "signed_in"}
        api.clock.advance(seconds=1)

    names = [row["display_name"] for row in api.query("SELECT display_name FROM user_account")]
    assert names == ["Ä" * 40, "Ä" * 40]


def test_a_deleted_user_label_in_a_longer_name_is_allowed(api: Api) -> None:
    code = _code(api, "nuova@example.org")

    response = api.verify(
        "nuova@example.org",
        code,
        registration={**REGISTRATION, "display_name": "Deleted user 142 fan"},
    )

    assert response.json() == {"outcome": "signed_in"}


def test_criterion_20_a_code_to_an_address_without_a_user_uses_the_pages_ui_language(
    api: Api,
) -> None:
    assert api.request_code("nuova@example.org", "en").status_code == 202

    (message,) = api.new_emails()

    assert message["Content-Language"] == "en"
    assert message["Subject"].endswith("Your sign-in code")


def test_criterion_20_a_new_users_preferred_language_is_that_of_the_registration_page(
    api: Api,
) -> None:
    code = _code(api, "nuova@example.org", "en")
    api.verify("nuova@example.org", code, "en", registration=REGISTRATION)

    assert api.client.get("/api/auth/session").json()["user"]["preferred_language"] == "en"
    api.clock.advance(minutes=1)
    api.request_code("nuova@example.org", "it")
    (message,) = api.new_emails()
    assert message["Content-Language"] == "en"


def test_an_unknown_page_language_falls_back_to_the_instance_default(api: Api) -> None:
    api.request_code("nuova@example.org", "de")

    (message,) = api.new_emails()

    assert message["Content-Language"] == "it"


def test_an_address_that_is_not_one_is_refused(api: Api) -> None:
    response = api.request_code("non-un-indirizzo")

    assert response.status_code == 400
    assert response.json() == {"code": "email_invalid"}


# Criterion 48: the neutral answer; Notifications criterion 29.


def test_criterion_48_the_answer_is_the_same_for_every_kind_of_address(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, migrated_database: str
) -> None:
    instance_with(tmp_path, monkeypatch, 'registration = "open"', 'registration = "invite"')
    with open_api(migrated_database) as invite:
        invite.add_user("registrata@example.org")
        invite.add_user("sospesa@example.org", suspended=True)
        answers = {
            email: invite.request_code(email)
            for email in (
                "registrata@example.org",
                "non-ammessa@example.org",
                "sospesa@example.org",
            )
        }
        sent = {message["To"]: message for message in invite.new_emails()}

    assert {
        (r.status_code, r.content, r.headers.get("content-type")) for r in answers.values()
    } == {(202, b"{}", "application/json")}
    assert sorted(sent) == ["non-ammessa@example.org", "registrata@example.org"]
    assert "Il tuo codice di accesso" in sent["registrata@example.org"]["Subject"]
    assert "Le registrazioni non sono aperte" in sent["non-ammessa@example.org"]["Subject"]


def test_criterion_48_an_unregistered_address_under_open_gets_the_same_answer(api: Api) -> None:
    api.add_user("registrata@example.org")

    registered = api.request_code("registrata@example.org")
    unregistered = api.request_code("nuova@example.org")

    assert (registered.status_code, registered.content) == (
        unregistered.status_code,
        unregistered.content,
    )


def test_notifications_criterion_29_registration_not_open_is_in_the_pages_language_with_no_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, migrated_database: str
) -> None:
    instance_with(tmp_path, monkeypatch, 'registration = "open"', 'registration = "closed"')
    with open_api(migrated_database) as closed:
        closed.request_code("nuova@example.org", "en")
        (message,) = closed.new_emails()
        codes = closed.query("SELECT email FROM sign_in_code")

    assert message["Content-Language"] == "en"
    assert message["Subject"].endswith("Registration is not open")
    text = message.get_body(("plain",))
    assert text is not None
    assert not any(line.strip().isdigit() for line in text.get_content().splitlines())
    assert codes == []


def test_a_suspended_users_code_issued_before_the_suspension_no_longer_signs_in(
    api: Api,
) -> None:
    user = api.add_user("persona@example.org")
    code = _code(api, "persona@example.org")
    api.query(
        "UPDATE user_account SET suspended_at = now(), suspension_reason = 'Prova' WHERE id = $1",
        user,
    )

    assert api.verify("persona@example.org", code).json() == {"code": "code_invalid"}


# Criterion 49: the honeypot.


def test_criterion_49_a_filled_honeypot_gets_the_ordinary_answer_and_nothing_is_sent(
    api: Api,
) -> None:
    api.add_user("persona@example.org")

    response = api.request_code("persona@example.org", website="https://spam.example")

    assert (response.status_code, response.content) == (202, b"{}")
    assert api.new_emails() == []
    assert api.query("SELECT email FROM sign_in_code") == []
    assert api.query("SELECT id FROM rate_limit_event") == []


# Criterion 47: rate limits.


def _status(api: Api, email: str, **extra: object) -> int:
    return api.request_code(email, **extra).status_code


def test_criterion_47_a_second_request_within_60_seconds_waits(api: Api) -> None:
    assert _status(api, "persona@example.org") == 202
    api.clock.advance(seconds=59)

    response = api.request_code("persona@example.org")

    assert response.status_code == 429
    assert response.json() == {"code": "rate_limited", "retry_after": 1}
    assert response.headers["Retry-After"] == "1"
    api.clock.advance(seconds=1)
    assert _status(api, "persona@example.org") == 202


def test_criterion_47_a_sixth_request_within_an_hour_waits(api: Api) -> None:
    for _ in range(5):
        assert _status(api, "persona@example.org") == 202
        api.clock.advance(seconds=61)

    response = api.request_code("persona@example.org")

    assert response.status_code == 429
    assert response.json()["retry_after"] == 3600 - 5 * 61
    api.clock.advance(seconds=3600 - 5 * 61)
    assert _status(api, "persona@example.org") == 202


def test_criterion_47_an_eleventh_request_within_24_hours_waits(api: Api) -> None:
    for _ in range(10):
        assert _status(api, "persona@example.org") == 202
        api.clock.advance(minutes=61)

    response = api.request_code("persona@example.org")

    assert response.status_code == 429
    assert response.json()["retry_after"] == 24 * 3600 - 10 * 61 * 60


def test_criterion_47_the_twenty_first_request_from_one_ip_within_an_hour_waits(
    api: Api,
) -> None:
    ip = {"X-Tart-Client-IP": "203.0.113.7"}
    for number in range(20):
        response = api.client.post(
            "/api/auth/code",
            json={"email": f"persona{number}@example.org", "language": "it"},
            headers=ip,
        )
        assert response.status_code == 202

    response = api.client.post(
        "/api/auth/code", json={"email": "altra@example.org", "language": "it"}, headers=ip
    )
    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    other = {"X-Tart-Client-IP": "203.0.113.8"}
    response = api.client.post(
        "/api/auth/code", json={"email": "altra@example.org", "language": "it"}, headers=other
    )
    assert response.status_code == 202


def test_criterion_47_a_refused_request_counts_for_nothing(api: Api) -> None:
    api.request_code("persona@example.org")
    for _ in range(3):
        api.clock.advance(seconds=10)
        assert _status(api, "persona@example.org") == 429

    api.clock.advance(seconds=30)

    assert _status(api, "persona@example.org") == 202


def test_criterion_47_no_limit_locks_an_account(api: Api) -> None:
    api.add_user("persona@example.org")
    code = _code(api, "persona@example.org")
    assert _status(api, "persona@example.org") == 429

    # The code already sent still signs in, and so does an open session.
    assert api.verify("persona@example.org", code).json() == {"outcome": "signed_in"}
    assert api.client.get("/api/auth/session").json()["user"] is not None


# Criterion 53: counters in PostgreSQL, IP addresses, X-Forwarded-For.


def _sweep(api: Api, at: datetime) -> None:
    async def run() -> None:
        engine = create_engine(api.dsn.replace("postgresql://", "postgresql+asyncpg://"))
        try:
            await sweep_database(engine, at)
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_criterion_53_counters_are_in_postgresql_and_gone_within_24_hours(api: Api) -> None:
    api.request_code("persona@example.org")
    ip_rows = api.query("SELECT name FROM rate_limit_event ORDER BY name")
    assert [row["name"] for row in ip_rows] == [
        "code_per_email_day",
        "code_per_email_hour",
        "code_per_email_minute",
        "code_per_ip_hour",
    ]
    stored = b"".join(
        bytes(row["key_hash"]) for row in api.query("SELECT key_hash FROM rate_limit_event")
    )
    assert b"testclient" not in stored and b"persona" not in stored

    _sweep(api, api.clock.now + timedelta(hours=1))
    assert "code_per_ip_hour" not in {
        row["name"] for row in api.query("SELECT name FROM rate_limit_event")
    }
    _sweep(api, api.clock.now + timedelta(hours=24))
    assert api.query("SELECT id FROM rate_limit_event") == []


def test_criterion_53_x_forwarded_for_is_ignored(api: Api) -> None:
    for number in range(20):
        response = api.client.post(
            "/api/auth/code",
            json={"email": f"persona{number}@example.org", "language": "it"},
            headers={"X-Forwarded-For": f"198.51.100.{number}"},
        )
        assert response.status_code == 202

    response = api.client.post(
        "/api/auth/code",
        json={"email": "altra@example.org", "language": "it"},
        headers={"X-Forwarded-For": "198.51.100.99"},
    )

    assert response.status_code == 429


# Criteria 13, 50: sessions.


def test_criterion_13_the_session_cookie_is_httponly_secure_and_samesite_lax(api: Api) -> None:
    api.add_user("persona@example.org")
    code = _code(api, "persona@example.org")

    response = api.verify("persona@example.org", code)

    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    attributes = {part.strip().split("=")[0].lower() for part in cookie.split(";")[1:]}
    assert {"httponly", "secure", "samesite", "path", "max-age"} <= attributes
    assert "samesite=lax" in cookie.lower()


def test_criterion_13_after_sign_out_the_same_session_id_is_rejected(api: Api) -> None:
    api.sign_in("persona@example.org")
    token = api.client.cookies[COOKIE]

    assert api.client.post("/api/auth/sign-out").status_code == 204

    api.client.cookies.set(COOKIE, token, domain=BASE_URL.removeprefix("https://"))
    assert api.client.get("/api/auth/session").json() == {"user": None}
    assert api.client.post("/api/auth/sign-out-everywhere").status_code == 401


def _with_token(api: Api, token: str) -> dict:
    api.client.cookies.clear()
    api.client.cookies.set(COOKIE, token, domain=BASE_URL.removeprefix("https://"))
    return api.client.get("/api/auth/session").json()


def test_criterion_50_a_session_is_refused_after_30_days_without_requests(api: Api) -> None:
    api.sign_in("persona@example.org")
    token = api.client.cookies[COOKIE]

    api.clock.advance(days=29, hours=23)
    assert _with_token(api, token)["user"] is not None
    api.clock.advance(days=29, hours=23)
    assert _with_token(api, token)["user"] is not None  # Extended by the last request.
    api.clock.advance(days=30)
    assert _with_token(api, token)["user"] is None


def test_criterion_50_a_session_is_refused_90_days_after_sign_in(api: Api) -> None:
    api.sign_in("persona@example.org")
    token = api.client.cookies[COOKIE]

    for _ in range(3):
        api.clock.advance(days=29)
        assert _with_token(api, token)["user"] is not None
    api.clock.advance(days=3)

    assert _with_token(api, token)["user"] is None


def test_criterion_50_a_request_extends_the_idle_expiry_at_most_once_a_day(api: Api) -> None:
    api.sign_in("persona@example.org")
    signed_in_at = api.clock.now

    api.clock.advance(hours=23)
    api.client.get("/api/auth/session")
    (row,) = api.query("SELECT last_seen_at FROM user_session")
    assert row["last_seen_at"] == signed_in_at

    api.clock.advance(hours=1)
    api.client.get("/api/auth/session")
    (row,) = api.query("SELECT last_seen_at FROM user_session")
    assert row["last_seen_at"] == api.clock.now


def test_criterion_50_each_sign_in_issues_a_new_session_id(api: Api) -> None:
    api.sign_in("persona@example.org")
    first = api.client.cookies[COOKIE]
    api.clock.advance(minutes=2)
    api.client.cookies.clear()

    api.sign_in("persona@example.org")

    assert api.client.cookies[COOKIE] != first
    assert len(api.query("SELECT id_hash FROM user_session")) == 2


def test_criterion_50_sign_out_everywhere_revokes_every_session_of_the_user(api: Api) -> None:
    api.sign_in("persona@example.org")
    first = api.client.cookies[COOKIE]
    api.clock.advance(minutes=2)
    api.client.cookies.clear()
    api.sign_in("persona@example.org")
    api.clock.advance(minutes=2)
    api.client.cookies.clear()
    api.sign_in("altra@example.org", "Altra persona")
    other = api.client.cookies[COOKIE]
    api.client.cookies.clear()
    api.client.cookies.set(COOKIE, first, domain=BASE_URL.removeprefix("https://"))

    assert api.client.post("/api/auth/sign-out-everywhere").status_code == 204

    assert _with_token(api, first)["user"] is None
    assert len(api.query("SELECT id_hash FROM user_session")) == 1
    assert _with_token(api, other)["user"]["display_name"] == "Altra persona"


def test_a_suspended_users_open_session_is_refused(api: Api) -> None:
    user = api.sign_in("persona@example.org")

    api.query(
        "UPDATE user_account SET suspended_at = now(), suspension_reason = 'Prova' WHERE id = $1",
        user,
    )

    assert api.client.get("/api/auth/session").json() == {"user": None}


# Criterion 17 (the API side): the role is read on every request.


def test_criterion_17_the_session_says_whether_the_user_is_a_moderator(api: Api) -> None:
    user = api.sign_in("persona@example.org")
    assert api.client.get("/api/auth/session").json()["user"]["moderator"] is False

    api.query("INSERT INTO user_role (user_id, role) VALUES ($1, 'moderator')", user)
    assert api.client.get("/api/auth/session").json()["user"]["moderator"] is True

    api.query("DELETE FROM user_role WHERE user_id = $1", user)
    assert api.client.get("/api/auth/session").json()["user"]["moderator"] is False


# Criterion 14: CSRF.


def test_criterion_14_a_state_changing_request_without_the_custom_header_is_refused(
    api: Api,
) -> None:
    bare = TestClient(api.client.app, base_url=BASE_URL)
    without = bare.post("/api/auth/code", json={"email": "persona@example.org", "language": "it"})

    assert without.status_code == 403
    assert without.json() == {"code": "csrf_refused"}


@pytest.mark.parametrize("origin", ["https://evil.example", "null", "http://archive.example.org"])
def test_criterion_14_a_state_changing_request_from_a_foreign_origin_is_refused(
    api: Api, origin: str
) -> None:
    response = api.client.post("/api/auth/sign-out", headers={"Origin": origin})

    assert response.status_code == 403
    assert response.json() == {"code": "csrf_refused"}


def test_criterion_14_the_sites_own_origin_is_accepted(api: Api) -> None:
    response = api.client.post("/api/auth/sign-out", headers={"Origin": BASE_URL})

    assert response.status_code == 204


def test_criterion_14_reads_need_no_custom_header(api: Api) -> None:
    bare = TestClient(api.client.app, base_url=BASE_URL)

    assert bare.get("/api/auth/session").json() == {"user": None}


def test_criterion_53_caddy_sets_the_client_ip_header_on_every_proxied_request() -> None:
    caddyfile = (Path(__file__).parents[2] / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    proxies = re.findall(r"reverse_proxy (\S+) \{\n(.*?)\n\t*\}", caddyfile, re.DOTALL)

    assert {upstream for upstream, _ in proxies} == {"api:8000", "frontend:3000"}
    assert caddyfile.count("reverse_proxy") == len(proxies)
    for upstream, block in proxies:
        assert "header_up X-Tart-Client-IP {client_ip}" in block, upstream
