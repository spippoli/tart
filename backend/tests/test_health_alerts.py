"""Alerting (Operations and portability spec, 5. Monitoring): the Operator alert email,
at most once per check per day, against PostgreSQL with a controlled clock."""

import asyncio
from datetime import UTC, datetime, timedelta
from email.headerregistry import Address
from email.message import EmailMessage
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from test_health import heartbeat

from tart import jobs
from tart.db import create_engine
from tart.email import CapturingEmailSender, Mailer
from tart.health import Check, Report, Settings, Status
from tart.health.alerts import Alerting, send_alerts
from tart.messages import load_catalogue
from tart.storage.filesystem import FilesystemStorage

NOW = datetime(2026, 10, 12, 1, 30, tzinfo=UTC)  # 03:30 in Rome
OPERATOR = "alerts@operator.example.org"
ALERTING = Alerting(OPERATOR, ZoneInfo("Europe/Rome"))
DISK_FULL = Check("disk", Status.FAIL, 12.5, 20, "percent")
NO_WORKER = Check("worker_heartbeat", Status.FAIL, None, 120, "seconds")
BACKUP_WARNING = Check("backup", Status.WARNING, "not_configured", 93600, "seconds")


def _mailer(sender: object | None = None) -> Mailer:
    return Mailer(
        catalogue=load_catalogue(),
        sender=sender or CapturingEmailSender(),  # type: ignore[arg-type]
        from_address=Address("Archivio di prova dell'arte urbana", "archive", "example.org"),
        archive_name="Archivio di prova dell'arte urbana",
        ui_languages=("it", "en"),
    )


def alert(
    database_url: str,
    mailer: Mailer,
    *checks: Check,
    now: datetime = NOW,
    alerting: Alerting = ALERTING,
) -> list[str]:
    async def run() -> list[str]:
        engine = create_engine(database_url)
        try:
            return await send_alerts(engine, mailer, alerting, Report(checks), now)
        finally:
            await engine.dispose()

    return asyncio.run(run())


def sent(mailer: Mailer) -> list[EmailMessage]:
    assert isinstance(mailer.sender, CapturingEmailSender)
    return mailer.sender.sent


def _text(message: EmailMessage) -> str:
    body = message.get_body(("plain",))
    assert body is not None
    return body.get_content()


# Criterion 17.


def test_criterion_17_a_failing_check_emails_the_operator_in_the_default_ui_language(
    migrated_database: str,
) -> None:
    mailer = _mailer()

    assert alert(migrated_database, mailer, DISK_FULL, BACKUP_WARNING) == ["disk"]

    (message,) = sent(mailer)
    assert message["To"] == OPERATOR
    assert message["Content-Language"] == "it"
    assert message["Subject"] == (
        "[Archivio di prova dell'arte urbana] Controllo di salute in errore: disk"
    )
    text = _text(message)
    # Key, value, and threshold untranslated, as in /api/health/details.
    assert "Il controllo di salute disk" in text
    assert "Valore: 12.5 percent\nSoglia: 20 percent" in text
    # The time in the Instance time zone.
    assert "2026-10-12 03:30 (Europe/Rome)" in text


def test_criterion_17_no_second_email_for_the_same_check_within_a_day(
    migrated_database: str,
) -> None:
    mailer = _mailer()
    alert(migrated_database, mailer, DISK_FULL)

    assert alert(migrated_database, mailer, DISK_FULL, now=NOW + timedelta(hours=23)) == []
    # Another check has its own day.
    assert alert(migrated_database, mailer, DISK_FULL, NO_WORKER, now=NOW + timedelta(hours=1)) == [
        "worker_heartbeat"
    ]
    assert alert(migrated_database, mailer, DISK_FULL, now=NOW + timedelta(days=1)) == ["disk"]

    assert [message["Subject"].split(": ")[-1] for message in sent(mailer)] == [
        "disk",
        "worker_heartbeat",
        "disk",
    ]
    assert "Valore: -\nSoglia: 120 seconds" in _text(sent(mailer)[1])


def test_criterion_17_without_an_alert_address_nothing_is_sent(migrated_database: str) -> None:
    mailer = _mailer()

    assert (
        alert(migrated_database, mailer, DISK_FULL, alerting=Alerting(None, ALERTING.time_zone))
        == []
    )

    assert sent(mailer) == []


def test_criterion_17_an_email_that_could_not_be_sent_is_tried_again(
    migrated_database: str,
) -> None:
    class Down:
        async def send(self, message: EmailMessage) -> None:
            raise OSError("connection refused")

    assert alert(migrated_database, _mailer(Down()), DISK_FULL) == []

    mailer = _mailer()
    assert alert(migrated_database, mailer, DISK_FULL, now=NOW + timedelta(minutes=1)) == ["disk"]


def test_criterion_17_the_worker_job_runs_the_checks_and_alerts(
    migrated_database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A healthy Instance apart from the worker heartbeat: nobody has started a worker.
    heartbeat(migrated_database.replace("+asyncpg", ""), datetime.now(UTC) - timedelta(hours=1))
    mailer = _mailer()

    async def run() -> None:
        engine = create_engine(migrated_database)
        context = SimpleNamespace(
            additional_context={
                jobs.ENGINE: engine,
                jobs.STORAGE: FilesystemStorage(tmp_path / "storage"),
                jobs.MAILER: mailer,
                jobs.HEALTH: Settings(disk_path=tmp_path, disk_min_free_percent=0),
                jobs.ALERTING: ALERTING,
            }
        )
        try:
            await jobs.health_alerts(context, 0)  # type: ignore[arg-type]
        finally:
            await engine.dispose()

    asyncio.run(run())

    (message,) = sent(mailer)
    assert message["Subject"].endswith(": worker_heartbeat")
