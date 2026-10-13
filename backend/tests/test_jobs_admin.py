"""Failed jobs and completed-job cleanup (Operations and portability spec, 5. Monitoring,
Jobs; 7. Operator CLI additions), against PostgreSQL."""

import asyncio
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from types import SimpleNamespace

import asyncpg
import pytest
from procrastinate import App, RetryStrategy
from test_health import check, failed_job
from test_health_alerts import _mailer

from tart import jobs
from tart.cli import main as run_cli
from tart.health import Status

SECRET_CODE = "482913"
ADDRESS = "person@example.org"


def _query(dsn: str, sql: str, *args: object) -> list[asyncpg.Record]:
    async def run() -> list[asyncpg.Record]:
        connection = await asyncpg.connect(dsn)
        try:
            return await connection.fetch(sql, *args)
        finally:
            await connection.close()

    return asyncio.run(run())


def _statuses(dsn: str) -> dict[str, str]:
    rows = _query(dsn, "SELECT task_name, status FROM procrastinate_jobs ORDER BY id")
    return {row["task_name"]: row["status"] for row in rows}


class Down:
    async def send(self, message: EmailMessage) -> None:
        raise OSError(f"550 mailbox unavailable: {ADDRESS}")


def _run_failing_jobs(database_url: str) -> None:
    """A task that fails on each of its two attempts, and an email the SMTP server refuses."""
    # Only these two tasks: the periodic ones would run too.
    app = App(connector=jobs.connector_for(database_url))
    app.task(name=jobs.SEND_EMAIL, pass_context=True)(jobs.send_email)

    @app.task(name="always_fails", retry=RetryStrategy(max_attempts=1, wait=0))
    def always_fails() -> None:
        raise RuntimeError("fictional failure")

    async def run() -> None:
        async with app.open_async():
            await app.configure_task("always_fails").defer_async()
            await app.configure_task(jobs.SEND_EMAIL).defer_async(
                kind="sign_in_code",
                to=ADDRESS,
                language="it",
                params={"code": SECRET_CODE, "minutes": 15},
            )
            await app.run_worker_async(
                wait=False, additional_context={jobs.MAILER: _mailer(Down())}
            )

    asyncio.run(run())


@pytest.fixture
def dsn(migrated_database: str) -> str:
    return migrated_database.replace("+asyncpg", "")


# Criterion 20.


def test_criterion_20_a_job_that_exhausts_its_retries_stays_failed(
    migrated_database: str, dsn: str, tmp_path: Path
) -> None:
    _run_failing_jobs(migrated_database)

    assert _statuses(dsn) == {"always_fails": "failed", jobs.SEND_EMAIL: "failed"}
    (row,) = _query(dsn, "SELECT attempts FROM procrastinate_jobs WHERE task_name = 'always_fails'")
    assert row["attempts"] == 2  # run, retried once, then failed for good
    # The failed email counts towards the Email check.
    email = {item.key: item for item in check(migrated_database, tmp_path).checks}["email"]
    assert (email.status, email.value) == (Status.FAIL, 1)


def test_criterion_20_tart_jobs_failed_lists_failed_jobs_without_personal_data(
    migrated_database: str, dsn: str, capsys: pytest.CaptureFixture[str]
) -> None:
    _run_failing_jobs(migrated_database)
    capsys.readouterr()

    assert run_cli(["jobs", "failed"]) == 0

    out = capsys.readouterr().out
    ids = {
        row["task_name"]: row["id"]
        for row in _query(dsn, "SELECT id, task_name FROM procrastinate_jobs")
    }
    lines = out.splitlines()
    assert [line.split("\t")[:2] for line in lines] == [
        [f"#{ids['always_fails']}", "always_fails"],
        [f"#{ids[jobs.SEND_EMAIL]}", jobs.SEND_EMAIL],
    ]
    assert "2 attempt(s)" in lines[0]
    assert ADDRESS not in out and SECRET_CODE not in out and "sign_in_code" not in out


def test_criterion_20_tart_jobs_retry_queues_one_or_every_failed_job(
    migrated_database: str, dsn: str, capsys: pytest.CaptureFixture[str]
) -> None:
    _run_failing_jobs(migrated_database)
    ids = {
        row["task_name"]: row["id"]
        for row in _query(dsn, "SELECT id, task_name FROM procrastinate_jobs")
    }

    assert run_cli(["jobs", "retry", str(ids[jobs.SEND_EMAIL])]) == 0
    assert _statuses(dsn) == {"always_fails": "failed", jobs.SEND_EMAIL: "todo"}
    assert run_cli(["jobs", "retry", str(ids[jobs.SEND_EMAIL])]) == 1  # no longer failed
    assert "is not a failed job" in capsys.readouterr().err

    assert run_cli(["jobs", "retry", "--all"]) == 0
    assert _statuses(dsn) == {"always_fails": "todo", jobs.SEND_EMAIL: "todo"}
    assert run_cli(["jobs", "failed"]) == 0
    assert capsys.readouterr().out.endswith("no failed job\n")


def test_criterion_20_completed_jobs_are_deleted_after_30_days(
    migrated_database: str, dsn: str
) -> None:
    now = datetime.now(UTC)
    for task, status, finished in [
        ("old_success", "succeeded", now - timedelta(days=31)),
        ("recent_success", "succeeded", now - timedelta(days=29)),
    ]:
        _query(
            dsn,
            "WITH job AS (INSERT INTO procrastinate_jobs (queue_name, task_name, status) "
            "VALUES ('default', $1, $2::procrastinate_job_status) RETURNING id) "
            "INSERT INTO procrastinate_events (job_id, type, at) "
            "SELECT id, $2::text::procrastinate_job_event_type, $3 FROM job",
            task,
            status,
            finished,
        )
    failed_job(dsn, now - timedelta(days=60), task="old_failure")
    app = jobs.create_app(jobs.connector_for(migrated_database))

    async def run() -> None:
        async with app.open_async():
            await jobs.delete_completed_jobs(SimpleNamespace(app=app), 0)  # type: ignore[arg-type]

    asyncio.run(run())

    assert _statuses(dsn) == {"recent_success": "succeeded", "old_failure": "failed"}
