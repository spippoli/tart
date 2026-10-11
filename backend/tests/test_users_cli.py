"""Foundations spec, 2. Roles and Suspension, and 5. Operator CLI: `tart users`, and the
Moderator warnings of startup and `tart config check --database`.

The commands run against the same database as an API client, so that their effect
on open sessions and code requests is observed through the HTTP API.
"""

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from auth_fixtures import Api, instance_with, open_api
from fastapi.testclient import TestClient

from tart.api.app import create_app
from tart.cli import main as run_cli

REASON = "Pubblicazione ripetuta di foto altrui senza permesso"


@pytest.fixture
def api(migrated_database: str) -> Iterator[Api]:
    with open_api(migrated_database) as started:
        yield started


def _session(api: Api) -> dict:
    return api.client.get("/api/auth/session").json()


# Criterion 18: grant, revoke, list.


def test_criterion_18_grant_gives_the_role_to_an_existing_user(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    user = api.sign_in("persona@example.org")

    assert run_cli(["users", "grant", "moderator", "Persona@Example.org"]) == 0

    assert f"#{user} persona@example.org granted the Moderator role" in capsys.readouterr().out
    assert _session(api)["user"]["moderator"] is True


def test_criterion_18_grant_creates_the_user_with_the_role(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    status = run_cli(
        ["users", "grant", "moderator", "nuova@example.org", "--display-name", " Moderatrice "]
    )

    assert status == 0
    assert "created with the Moderator role" in capsys.readouterr().out
    (row,) = api.query(
        "SELECT display_name, preferred_language, role FROM user_account "
        "JOIN user_role ON user_id = id WHERE email = 'nuova@example.org'"
    )
    assert tuple(row) == ("Moderatrice", "it", "moderator")
    # The created User signs in with the ordinary code, without the registration step.
    assert api.request_code("nuova@example.org").status_code == 202
    (message,) = api.new_emails()
    assert api.verify("nuova@example.org", api.code_from(message)).json() == {
        "outcome": "signed_in"
    }
    assert _session(api)["user"]["moderator"] is True


@pytest.mark.parametrize(
    ("extra", "error"),
    [
        ([], "give --display-name to create one"),
        (["--display-name", "Utente eliminato 12"], "display_name_reserved"),
        (["--display-name", "  "], "display_name_length"),
    ],
)
def test_grant_refuses_to_create_a_user_without_a_valid_display_name(
    api: Api, capsys: pytest.CaptureFixture[str], extra: list[str], error: str
) -> None:
    assert run_cli(["users", "grant", "moderator", "nuova@example.org", *extra]) == 1

    assert error in capsys.readouterr().err
    assert api.query("SELECT id FROM user_account") == []


def test_grant_twice_says_the_user_already_holds_the_role(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    api.add_user("persona@example.org")
    run_cli(["users", "grant", "moderator", "persona@example.org"])

    assert run_cli(["users", "grant", "moderator", "persona@example.org"]) == 0

    assert "already holds the Moderator role" in capsys.readouterr().out


def test_criterion_18_after_revoke_the_next_request_of_an_open_session_is_not_a_moderators(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    api.sign_in("persona@example.org")
    run_cli(["users", "grant", "moderator", "persona@example.org"])
    assert _session(api)["user"]["moderator"] is True

    assert run_cli(["users", "revoke", "moderator", "persona@example.org"]) == 0

    assert "no longer holds the Moderator role" in capsys.readouterr().out
    # Still signed in, without the role: the frontend answers Moderation pages with a 403.
    user = _session(api)["user"]
    assert user is not None
    assert user["moderator"] is False


def test_revoke_of_an_unknown_address_fails(api: Api, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(["users", "revoke", "moderator", "nessuno@example.org"]) == 1

    assert "no User has the address nessuno@example.org" in capsys.readouterr().err


def test_criterion_18_list_shows_exactly_the_holders(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    first = api.add_user("prima@example.org")
    api.add_user("senza-ruolo@example.org")
    second = api.add_user("seconda@example.org", suspended=True)
    revoked = api.add_user("revocata@example.org")
    for email in ["prima@example.org", "seconda@example.org", "revocata@example.org"]:
        run_cli(["users", "grant", "moderator", email])
    run_cli(["users", "revoke", "moderator", "revocata@example.org"])
    capsys.readouterr()

    assert run_cli(["users", "list", "--role", "moderator"]) == 0

    assert capsys.readouterr().out.splitlines() == [
        f"#{first}\tprima@example.org\tUtente di prova",
        f"#{second}\tseconda@example.org\tUtente di prova\tsuspended since 2026-10-01",
    ]
    assert revoked not in (first, second)


def test_list_says_when_nobody_holds_the_role(api: Api, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(["users", "list", "--role", "moderator"]) == 0

    assert capsys.readouterr().out == "no User holds the Moderator role\n"


# Criteria 52 and Notifications 30: Suspension.


def test_criterion_52_suspend_refuses_open_sessions_and_code_requests_and_emails_the_reason(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    user = api.sign_in("persona@example.org")
    assert _session(api)["user"]["number"] == user

    assert run_cli(["users", "suspend", "persona@example.org", "--reason", REASON]) == 0

    assert "is suspended" in capsys.readouterr().out
    assert _session(api) == {"user": None}
    assert api.query("SELECT id_hash FROM user_session") == []
    (row,) = api.query("SELECT suspended_at, suspension_reason FROM user_account")
    assert row["suspended_at"] is not None
    assert row["suspension_reason"] == REASON
    (email,) = api.new_emails()
    assert email["To"] == "persona@example.org"
    assert REASON in email.get_body(("plain",)).get_content()
    # A code request answers as for anyone else, and sends nothing.
    api.clock.advance(minutes=1)
    response = api.request_code("persona@example.org")
    assert (response.status_code, response.json()) == (202, {})
    assert api.new_emails() == []


def test_criterion_52_unsuspend_restores_sign_in_and_clears_the_suspension(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    api.add_user("persona@example.org")
    run_cli(["users", "suspend", "persona@example.org", "--reason", REASON])
    api.new_emails()

    assert run_cli(["users", "unsuspend", "persona@example.org"]) == 0

    assert "may sign in again" in capsys.readouterr().out
    (row,) = api.query("SELECT suspended_at, suspension_reason FROM user_account")
    assert tuple(row) == (None, None)
    assert api.request_code("persona@example.org").status_code == 202
    (message,) = api.new_emails()
    assert api.verify("persona@example.org", api.code_from(message)).json() == {
        "outcome": "signed_in"
    }


def test_criterion_52_a_suspended_moderator_keeps_the_role_but_cannot_act(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    api.sign_in("persona@example.org")
    run_cli(["users", "grant", "moderator", "persona@example.org"])

    run_cli(["users", "suspend", "persona@example.org", "--reason", REASON])

    assert _session(api) == {"user": None}
    assert api.query("SELECT role FROM user_role")[0]["role"] == "moderator"


def test_notifications_criterion_30_the_suspension_email_replies_to_the_dsa_contact(
    api: Api,
) -> None:
    api.add_user("persona@example.org", language="en")

    run_cli(["users", "suspend", "persona@example.org", "--reason", REASON])

    (email,) = api.new_emails()
    assert email["Reply-To"] == "dsa@example.org"
    assert email["Content-Language"] == "en"
    assert email["Subject"].endswith("Your account is suspended")
    assert REASON in email.get_body(("plain",)).get_content()


def test_notifications_criterion_30_unsuspend_sends_nothing(api: Api) -> None:
    api.add_user("persona@example.org")
    run_cli(["users", "suspend", "persona@example.org", "--reason", REASON])
    api.new_emails()

    run_cli(["users", "unsuspend", "persona@example.org"])

    assert api.new_emails() == []


@pytest.mark.parametrize(
    ("command", "error"),
    [
        (["suspend", "persona@example.org", "--reason", "  "], "the reason may not be empty"),
        (["suspend", "nessuno@example.org", "--reason", REASON], "no User has the address"),
        (["suspend", "non-un-indirizzo", "--reason", REASON], "is not an email address"),
        (["unsuspend", "persona@example.org"], "is not suspended"),
    ],
)
def test_suspend_and_unsuspend_refuse_what_they_cannot_do(
    api: Api, capsys: pytest.CaptureFixture[str], command: list[str], error: str
) -> None:
    api.add_user("persona@example.org")

    assert run_cli(["users", *command]) == 1

    assert error in capsys.readouterr().err
    assert api.new_emails() == []


def test_suspending_a_suspended_user_again_is_refused(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    api.add_user("persona@example.org", suspended=True)

    assert run_cli(["users", "suspend", "persona@example.org", "--reason", REASON]) == 1

    assert "already suspended since 2026-10-01" in capsys.readouterr().err
    assert api.new_emails() == []


# Criterion 45: the Moderator warnings.


def _warnings(capsys: pytest.CaptureFixture[str]) -> list[str]:
    assert run_cli(["config", "check", "--database"]) == 0
    return [line for line in capsys.readouterr().err.splitlines() if line.startswith("warning:")]


def test_criterion_45_config_check_warns_when_nobody_holds_the_moderator_role(
    migrated_database: str, capsys: pytest.CaptureFixture[str]
) -> None:
    (warning,) = _warnings(capsys)

    assert "no User holds the Moderator role" in warning


def test_criterion_45_a_suspended_moderator_does_not_count(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    api.add_user("persona@example.org", suspended=True)
    run_cli(["users", "grant", "moderator", "persona@example.org"])
    capsys.readouterr()

    (warning,) = _warnings(capsys)

    assert "no User holds the Moderator role" in warning


@pytest.mark.parametrize(("moderators", "warned"), [(1, True), (2, False)])
def test_criterion_45_without_self_approval_config_check_warns_about_a_single_moderator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    api: Api,
    capsys: pytest.CaptureFixture[str],
    moderators: int,
    warned: bool,
) -> None:
    instance_with(tmp_path, monkeypatch, "self_approval = true", "self_approval = false")
    for number in range(moderators):
        api.add_user(f"moderatrice{number}@example.org")
        run_cli(["users", "grant", "moderator", f"moderatrice{number}@example.org"])
    capsys.readouterr()

    warnings = _warnings(capsys)

    assert bool(warnings) is warned
    assert all("self_approval is false" in warning for warning in warnings)


def test_criterion_45_with_self_approval_one_moderator_is_enough(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    api.add_user("persona@example.org")
    run_cli(["users", "grant", "moderator", "persona@example.org"])
    capsys.readouterr()

    assert _warnings(capsys) == []


def test_criterion_45_startup_logs_the_warning_and_still_starts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    migrated_database: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    instance_with(tmp_path, monkeypatch, "self_approval = true", "self_approval = false")

    with (
        caplog.at_level(logging.WARNING, logger="tart.startup"),
        TestClient(create_app()) as client,
    ):
        assert client.get("/api/health").status_code == 200

    assert any("no User holds the Moderator role" in record.message for record in caplog.records)
