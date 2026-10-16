"""Contribution and moderation spec, Invitations (criterion 36) and Foundations criterion 19:
issuing, listing, revoking, and redeeming Invitations under `registration = invite`.

The emails are not tested: the invitation email belongs to the Notifications spec.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from auth_fixtures import Api, instance_with, open_api

from tart.cli import main as run_cli

REGISTRATION = {"display_name": "Persona invitata", "age_confirmed": True}
ENDPOINT = "/api/moderation/invitations"


@pytest.fixture
def invite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, migrated_database: str
) -> Iterator[Api]:
    instance_with(tmp_path, monkeypatch, 'registration = "open"', 'registration = "invite"')
    with open_api(migrated_database) as api:
        yield api


def _moderator(api: Api, email: str = "moderatrice@example.org") -> int:
    user = api.add_user(email)
    api.query("INSERT INTO user_role (user_id, role) VALUES ($1, 'moderator')", user)
    assert api.request_code(email).status_code == 202
    (message,) = api.new_emails()
    assert api.verify(email, api.code_from(message)).json() == {"outcome": "signed_in"}
    return user


def _register(api: Api, email: str):
    """Ask for a code and try to register with it; the response to the last step."""
    assert api.request_code(email).status_code == 202
    (message,) = api.new_emails()
    if "Le registrazioni non sono aperte" in message["Subject"]:
        return None
    return api.verify(email, api.code_from(message), registration=REGISTRATION)


def _issue(api: Api, email: str):
    return api.client.post(ENDPOINT, json={"email": email})


def _statuses(api: Api) -> dict[str, str]:
    items = api.client.get(ENDPOINT).json()["items"]
    return {item["email"]: item["status"] for item in items}


# Foundations criterion 19: who can register under `invite`.


def test_foundations_criterion_19_an_address_with_a_pending_invitation_registers_without_a_role(
    invite: Api,
) -> None:
    _moderator(invite)
    _issue(invite, "Invitata@Example.org")
    invite.client.post("/api/auth/sign-out")

    response = _register(invite, "invitata@example.org")

    assert response is not None
    assert response.json() == {"outcome": "signed_in"}
    session = invite.client.get("/api/auth/session").json()["user"]
    assert session["moderator"] is False
    assert invite.query("SELECT role FROM user_role WHERE user_id = $1", session["number"]) == []


def test_foundations_criterion_19_an_address_without_an_invitation_cannot_register(
    invite: Api,
) -> None:
    assert _register(invite, "sconosciuta@example.org") is None
    assert invite.query("SELECT id FROM user_account") == []


def test_foundations_criterion_19_an_expired_invitation_does_not_admit(invite: Api) -> None:
    _moderator(invite)
    _issue(invite, "tardiva@example.org")
    invite.client.post("/api/auth/sign-out")
    invite.clock.advance(days=14, seconds=1)

    assert _register(invite, "tardiva@example.org") is None


def test_foundations_criterion_19_a_used_invitation_does_not_admit_again(invite: Api) -> None:
    _moderator(invite)
    _issue(invite, "una-volta@example.org")
    invite.client.post("/api/auth/sign-out")
    assert _register(invite, "una-volta@example.org") is not None
    user = invite.client.get("/api/auth/session").json()["user"]["number"]
    invite.client.post("/api/auth/sign-out")
    # The account is deleted (a later spec); the Invitation does not come back.
    invite.query("DELETE FROM user_account WHERE id = $1", user)
    invite.clock.advance(minutes=2)

    assert _register(invite, "una-volta@example.org") is None


# Criterion 36: single use, its address, 14 days, revocation, only under `invite`.


def test_criterion_36_an_invitation_is_redeemed_once_and_marks_who_used_it(invite: Api) -> None:
    moderator = _moderator(invite)
    _issue(invite, "invitata@example.org")
    invite.client.post("/api/auth/sign-out")
    _register(invite, "invitata@example.org")
    user = invite.client.get("/api/auth/session").json()["user"]["number"]
    invite.client.post("/api/auth/sign-out")
    invite.clock.advance(minutes=2)
    invite.sign_in("moderatrice@example.org")

    (row,) = invite.query("SELECT issued_by, used_by, used_at FROM invitation")

    assert (row["issued_by"], row["used_by"]) == (moderator, user)
    assert row["used_at"] is not None
    assert _statuses(invite) == {"invitata@example.org": "used"}


def test_criterion_36_an_invitation_admits_only_its_own_address(invite: Api) -> None:
    _moderator(invite)
    _issue(invite, "invitata@example.org")
    invite.client.post("/api/auth/sign-out")

    assert _register(invite, "un-altra@example.org") is None
    assert _register(invite, "invitata@example.org") is not None


def test_criterion_36_an_invitation_is_valid_for_fourteen_days(invite: Api) -> None:
    _moderator(invite)
    _issue(invite, "puntuale@example.org")
    invite.client.post("/api/auth/sign-out")
    invite.clock.advance(days=13, hours=23)

    response = _register(invite, "puntuale@example.org")

    assert response is not None
    assert response.json() == {"outcome": "signed_in"}


def test_criterion_36_a_code_requested_in_time_does_not_register_after_expiry(
    invite: Api,
) -> None:
    _moderator(invite)
    _issue(invite, "tardiva@example.org")
    invite.client.post("/api/auth/sign-out")
    invite.clock.advance(days=13, hours=23, minutes=55)
    invite.request_code("tardiva@example.org")
    (message,) = invite.new_emails()
    invite.clock.advance(minutes=6)

    response = invite.verify(
        "tardiva@example.org", invite.code_from(message), registration=REGISTRATION
    )

    assert response.status_code == 400
    assert response.json() == {"code": "code_invalid"}


def test_criterion_36_a_revoked_invitation_does_not_admit(invite: Api) -> None:
    _moderator(invite)
    created = _issue(invite, "ripensata@example.org").json()
    assert invite.client.post(f"{ENDPOINT}/{created['id']}/revoke").status_code == 204
    invite.client.post("/api/auth/sign-out")

    assert _register(invite, "ripensata@example.org") is None


def test_criterion_36_invitations_cannot_be_issued_unless_registration_is_invite(
    api: Api,
) -> None:
    _moderator(api)

    response = _issue(api, "invitata@example.org")

    assert response.status_code == 409
    assert response.json() == {"code": "registration_not_invite"}
    assert api.query("SELECT id FROM invitation") == []


def test_criterion_36_the_cli_refuses_unless_registration_is_invite(
    migrated_database: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with open_api(migrated_database) as api:
        status = run_cli(["invites", "create", "invitata@example.org"])

        assert status == 1
        assert "registration = invite" in capsys.readouterr().err
        assert api.query("SELECT id FROM invitation") == []


@pytest.fixture
def api(migrated_database: str) -> Iterator[Api]:
    with open_api(migrated_database) as started:
        yield started


# The Moderator-facing API.


def test_issuing_listing_and_revoking_need_the_moderator_role(invite: Api) -> None:
    anonymous = invite.client.get(ENDPOINT)
    invite.add_user("persona@example.org")
    invite.sign_in("persona@example.org")
    attempts = [
        invite.client.get(ENDPOINT),
        _issue(invite, "invitata@example.org"),
        invite.client.post(f"{ENDPOINT}/1/revoke"),
    ]

    assert (anonymous.status_code, anonymous.json()) == (401, {"code": "sign_in_required"})
    assert [(r.status_code, r.json()) for r in attempts] == [(403, {"code": "moderator_only"})] * 3


def test_an_invitation_records_its_issuer_and_the_list_shows_every_status(invite: Api) -> None:
    moderator = _moderator(invite)
    invite.query("UPDATE user_account SET display_name = 'Moderatrice' WHERE id = $1", moderator)
    for email in ("in-attesa@example.org", "usata@example.org", "scaduta@example.org"):
        assert _issue(invite, email).status_code == 201
    invite.query(
        "UPDATE invitation SET expires_at = $1 WHERE email = 'scaduta@example.org'",
        invite.clock.now,
    )
    invite.client.post("/api/auth/sign-out")
    _register(invite, "usata@example.org")
    invite.client.post("/api/auth/sign-out")
    invite.clock.advance(minutes=2)
    invite.sign_in("moderatrice@example.org")
    assert run_cli(["invites", "create", "dal-terminale@example.org"]) == 0

    body = invite.client.get(ENDPOINT).json()["items"]
    by_email = {item["email"]: item for item in body}

    assert {email: item["status"] for email, item in by_email.items()} == {
        "in-attesa@example.org": "pending",
        "usata@example.org": "used",
        "scaduta@example.org": "expired",
        "dal-terminale@example.org": "pending",
    }
    assert by_email["in-attesa@example.org"]["issuer"] == {
        "number": moderator,
        "display_name": "Moderatrice",
    }
    assert by_email["dal-terminale@example.org"]["issuer"] is None


def test_any_moderator_can_revoke_a_pending_invitation_but_not_another_kind(
    invite: Api,
) -> None:
    _moderator(invite)
    pending = _issue(invite, "in-attesa@example.org").json()
    used = _issue(invite, "usata@example.org").json()
    invite.client.post("/api/auth/sign-out")
    _register(invite, "usata@example.org")
    invite.client.post("/api/auth/sign-out")
    second = _moderator(invite, "seconda@example.org")

    revoked = invite.client.post(f"{ENDPOINT}/{pending['id']}/revoke")
    again = invite.client.post(f"{ENDPOINT}/{pending['id']}/revoke")
    on_used = invite.client.post(f"{ENDPOINT}/{used['id']}/revoke")
    missing = invite.client.post(f"{ENDPOINT}/999/revoke")

    assert revoked.status_code == 204
    assert (again.status_code, again.json()) == (409, {"code": "invitation_not_pending"})
    assert on_used.status_code == 409
    assert (missing.status_code, missing.json()) == (404, {"code": "invitation_not_found"})
    assert _statuses(invite)["in-attesa@example.org"] == "revoked"
    (row,) = invite.query("SELECT revoked_by FROM invitation WHERE id = $1", pending["id"])
    assert row["revoked_by"] == second


def test_issuing_refuses_a_bad_address_and_a_second_pending_invitation(invite: Api) -> None:
    _moderator(invite)
    assert _issue(invite, "in-attesa@example.org").status_code == 201

    bad = _issue(invite, "non-un-indirizzo")
    twice = _issue(invite, "In-Attesa@example.org")

    assert (bad.status_code, bad.json()) == (400, {"code": "email_invalid"})
    assert (twice.status_code, twice.json()) == (409, {"code": "invitation_pending"})


def test_a_former_moderators_pending_invitations_stay_valid(invite: Api) -> None:
    moderator = _moderator(invite)
    _issue(invite, "invitata@example.org")
    invite.client.post("/api/auth/sign-out")
    invite.query("DELETE FROM user_role WHERE user_id = $1", moderator)

    response = _register(invite, "invitata@example.org")

    assert response is not None
    assert response.json() == {"outcome": "signed_in"}
    (row,) = invite.query("SELECT issued_by FROM invitation")
    assert row["issued_by"] == moderator


def test_the_cli_creates_an_invitation_issued_by_the_operator(
    invite: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    status = run_cli(["invites", "create", "Operatore@Example.org"])

    assert status == 0
    assert "operatore@example.org" in capsys.readouterr().out
    (row,) = invite.query(
        "SELECT email, issued_by, expires_at - created_at AS lifetime FROM invitation"
    )
    assert (row["email"], row["issued_by"]) == ("operatore@example.org", None)
    assert row["lifetime"].days == 14
    assert _register(invite, "operatore@example.org") is not None
