"""Health (Operations and portability spec, 5. Monitoring): the checks at, below, and
above their thresholds, against PostgreSQL and a filesystem storage, with a
controlled clock; and the two endpoints."""

import asyncio
from collections import namedtuple
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg
import pytest
from auth_fixtures import Api, open_api
from conftest import ENVIRONMENT

from tart import health
from tart.api.health import get_cache_seconds
from tart.config.loader import load_environment
from tart.db import create_engine
from tart.health import Report, Services, Settings, Status, run_checks
from tart.storage.filesystem import FilesystemStorage

NOW = datetime.now(UTC).replace(microsecond=0)
KEYS = [
    "database",
    "storage",
    "worker_heartbeat",
    "job_queue",
    "email",
    "disk",
    "backup",
    "verify",
]
TOKEN = "health-details-token-0123456789abcdef"
Usage = namedtuple("Usage", "total used free")


def _execute(dsn: str, statement: str, *args: object) -> None:
    async def run() -> None:
        connection = await asyncpg.connect(dsn)
        try:
            await connection.execute(statement, *args)
        finally:
            await connection.close()

    asyncio.run(run())


def heartbeat(dsn: str, at: datetime) -> None:
    _execute(dsn, "INSERT INTO procrastinate_workers (last_heartbeat) VALUES ($1)", at)


def queued_job(dsn: str, due: datetime, task: str = "process_upload") -> None:
    _execute(
        dsn,
        "INSERT INTO procrastinate_jobs (queue_name, task_name, status, scheduled_at) "
        "VALUES ('default', $1, 'todo', $2)",
        task,
        due,
    )


def failed_job(dsn: str, failed_at: datetime, task: str = "send_email") -> None:
    _execute(
        dsn,
        "WITH job AS (INSERT INTO procrastinate_jobs (queue_name, task_name, status, args) "
        "VALUES ('default', $1, 'failed', '{\"to\": \"person@example.org\"}') RETURNING id) "
        "INSERT INTO procrastinate_events (job_id, type, at) SELECT id, 'failed', $2 FROM job",
        task,
        failed_at,
    )


def succeeded(dsn: str, operation: str, at: datetime) -> None:
    _execute(
        dsn,
        "INSERT INTO operation_success (operation, succeeded_at) VALUES ($1, $2)",
        operation,
        at,
    )


@pytest.fixture
def dsn(migrated_database: str) -> str:
    return migrated_database.replace("+asyncpg", "")


@pytest.fixture
def disk(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[float]]:
    """The disk's free share, in percent, as the disk check reads it."""
    free = [50.0]
    monkeypatch.setattr(
        health.shutil,
        "disk_usage",
        lambda _: Usage(1000, 1000 - int(free[0] * 10), int(free[0] * 10)),
    )
    yield free


def check(
    database_url: str, tmp_path: Path, settings: Settings | None = None, now: datetime = NOW
) -> Report:
    async def run() -> Report:
        engine = create_engine(database_url)
        try:
            storage = FilesystemStorage(tmp_path / "storage")
            return await run_checks(Services(engine, storage), settings or Settings(), now)
        finally:
            await engine.dispose()

    return asyncio.run(run())


def by_key(report: Report) -> dict[str, health.Check]:
    return {item.key: item for item in report.checks}


def healthy(dsn: str) -> None:
    heartbeat(dsn, NOW - timedelta(seconds=10))


def test_a_healthy_instance_reports_every_check_in_order(
    migrated_database: str, dsn: str, tmp_path: Path, disk: list[float]
) -> None:
    healthy(dsn)

    report = check(migrated_database, tmp_path)

    assert [item.key for item in report.checks] == KEYS
    assert report.status is Status.OK
    assert {item.key: item.status for item in report.checks} == {
        **dict.fromkeys(KEYS, Status.OK),
        "backup": Status.WARNING,
        "verify": Status.WARNING,
    }
    # The storage probe leaves nothing behind.
    assert not any(path.is_file() for path in (tmp_path / "storage").rglob("*"))


# Criterion 8, as Health reads it: without backups, a warning.


def test_criterion_8_without_backups_the_backup_check_is_a_not_configured_warning(
    migrated_database: str, dsn: str, tmp_path: Path, disk: list[float]
) -> None:
    healthy(dsn)

    checks = by_key(check(migrated_database, tmp_path))

    assert (checks["backup"].status, checks["backup"].value) == (Status.WARNING, "not_configured")
    assert (checks["verify"].status, checks["verify"].value) == (Status.WARNING, "not_configured")


@pytest.mark.parametrize(
    ("age", "status"), [(119, Status.OK), (120, Status.FAIL), (121, Status.FAIL)]
)
def test_the_worker_heartbeat_must_be_younger_than_two_minutes(
    migrated_database: str, dsn: str, tmp_path: Path, disk: list[float], age: int, status: Status
) -> None:
    heartbeat(dsn, NOW - timedelta(seconds=age))

    worker = by_key(check(migrated_database, tmp_path))["worker_heartbeat"]

    assert (worker.status, worker.value, worker.threshold, worker.unit) == (
        status,
        age,
        120,
        "seconds",
    )


def test_without_a_worker_the_heartbeat_check_fails(
    migrated_database: str, tmp_path: Path, disk: list[float]
) -> None:
    worker = by_key(check(migrated_database, tmp_path))["worker_heartbeat"]

    assert (worker.status, worker.value) == (Status.FAIL, None)


@pytest.mark.parametrize(
    ("age", "status"), [(899, Status.OK), (900, Status.FAIL), (901, Status.FAIL)]
)
def test_the_oldest_queued_job_must_be_younger_than_15_minutes(
    migrated_database: str, dsn: str, tmp_path: Path, disk: list[float], age: int, status: Status
) -> None:
    queued_job(dsn, NOW - timedelta(seconds=age))
    queued_job(dsn, NOW - timedelta(seconds=30))
    # A job scheduled for later is not waiting yet.
    queued_job(dsn, NOW + timedelta(hours=2))

    queue = by_key(check(migrated_database, tmp_path))["job_queue"]

    assert (queue.status, queue.value, queue.threshold) == (status, age, 900)


def test_an_empty_queue_is_healthy(
    migrated_database: str, tmp_path: Path, disk: list[float]
) -> None:
    queue = by_key(check(migrated_database, tmp_path))["job_queue"]

    assert (queue.status, queue.value) == (Status.OK, 0)


def test_one_email_failed_in_the_last_24_hours_fails_the_email_check(
    migrated_database: str, dsn: str, tmp_path: Path, disk: list[float]
) -> None:
    failed_job(dsn, NOW - timedelta(hours=25))  # too old to count
    failed_job(dsn, NOW - timedelta(minutes=5), task="process_upload")  # not an email
    assert by_key(check(migrated_database, tmp_path))["email"].status is Status.OK

    failed_job(dsn, NOW - timedelta(hours=23))

    email = by_key(check(migrated_database, tmp_path))["email"]
    assert (email.status, email.value, email.threshold) == (Status.FAIL, 1, 0)
    # At the threshold, healthy: the override allows one.
    relaxed = by_key(check(migrated_database, tmp_path, Settings(email_max_failed=1)))["email"]
    assert relaxed.status is Status.OK


@pytest.mark.parametrize(
    ("free", "status"), [(20.1, Status.OK), (20.0, Status.FAIL), (19.9, Status.FAIL)]
)
def test_free_disk_must_be_above_20_percent(
    migrated_database: str,
    dsn: str,
    tmp_path: Path,
    disk: list[float],
    free: float,
    status: Status,
) -> None:
    disk[0] = free

    item = by_key(check(migrated_database, tmp_path))["disk"]

    assert (item.status, item.value, item.threshold, item.unit) == (status, free, 20, "percent")


@pytest.mark.parametrize(
    ("operation", "max_age"), [("backup", 26 * 3600), ("verify", 8 * 24 * 3600)]
)
def test_with_backups_the_last_success_must_be_recent_enough(
    migrated_database: str,
    dsn: str,
    tmp_path: Path,
    disk: list[float],
    operation: str,
    max_age: int,
) -> None:
    settings = Settings(backups_configured=True)
    never = by_key(check(migrated_database, tmp_path, settings))[operation]
    assert (never.status, never.value, never.threshold) == (Status.FAIL, None, max_age)

    succeeded(dsn, operation, NOW - timedelta(seconds=max_age - 1))
    assert by_key(check(migrated_database, tmp_path, settings))[operation].status is Status.OK

    late = NOW + timedelta(seconds=1)
    after = by_key(check(migrated_database, tmp_path, settings, now=late))[operation]
    assert (after.status, after.value) == (Status.FAIL, max_age)


def test_an_unwritable_storage_fails_the_storage_check(
    migrated_database: str, dsn: str, tmp_path: Path, disk: list[float]
) -> None:
    healthy(dsn)
    (tmp_path / "storage").write_text("not a directory")

    report = check(migrated_database, tmp_path)

    storage = by_key(report)["storage"]
    assert (storage.status, storage.value, storage.threshold) == (
        Status.FAIL,
        "unreachable",
        "reachable",
    )
    assert report.status is Status.FAIL


def test_an_unreachable_database_fails_every_check_that_reads_it(
    tmp_path: Path, disk: list[float]
) -> None:
    report = check("postgresql+asyncpg://tart:tart@127.0.0.1:9/tart", tmp_path)

    checks = by_key(report)
    assert checks["database"].value == "unreachable"
    assert {key for key, item in checks.items() if item.status is Status.FAIL} == {
        "database",
        "worker_heartbeat",
        "job_queue",
        "email",
    }
    assert checks["email"].value is None
    assert report.status is Status.FAIL


def test_the_thresholds_default_to_the_spec_and_are_overridden_by_the_environment() -> None:
    environment = {**ENVIRONMENT, "DATABASE_URL": "postgresql+asyncpg://t:t@db/t"}

    assert Settings.from_environment(load_environment(environment)) == Settings()
    overridden = Settings.from_environment(
        load_environment(
            {
                **environment,
                "RESTIC_REPOSITORY": "sftp:backup@storage.example.org:/tart",
                "HEALTH_DISK_PATH": "/data",
                "HEALTH_WORKER_HEARTBEAT_MAX_AGE": "300",
                "HEALTH_JOB_QUEUE_MAX_AGE": "1800",
                "HEALTH_EMAIL_MAX_FAILED": "2",
                "HEALTH_DISK_MIN_FREE_PERCENT": "10",
                "HEALTH_BACKUP_MAX_AGE": "180000",
                "HEALTH_VERIFY_MAX_AGE": "1209600",
            }
        )
    )
    assert overridden == Settings(
        disk_path=Path("/data"),
        backups_configured=True,
        worker_heartbeat_max_age=300,
        job_queue_max_age=1800,
        email_max_failed=2,
        disk_min_free_percent=10,
        backup_max_age=180000,
        verify_max_age=1209600,
    )


# The endpoints.


@pytest.fixture
def api(
    migrated_database: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    disk: list[float],
) -> Iterator[Api]:
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "storage"))
    monkeypatch.setenv("HEALTH_DETAILS_TOKEN", TOKEN)
    with open_api(migrated_database) as started:
        started.client.app.dependency_overrides[get_cache_seconds] = lambda: 0  # type: ignore[attr-defined]
        started.clock.now = NOW
        yield started


def _details(api: Api, token: str | None = TOKEN):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return api.client.get("/api/health/details", headers=headers)


# Criterion 15.


def test_criterion_15_the_public_endpoint_answers_ok_and_nothing_else(api: Api) -> None:
    healthy(api.dsn)

    response = api.client.get("/api/health")

    assert (response.status_code, response.text) == (200, "ok")
    assert response.headers["content-type"].startswith("text/plain")


def test_criterion_15_any_failing_check_turns_the_public_endpoint_to_fail(api: Api) -> None:
    healthy(api.dsn)
    failed_job(api.dsn, NOW - timedelta(minutes=1))

    response = api.client.get("/api/health")

    assert (response.status_code, response.text) == (503, "fail")


def test_criterion_15_a_warning_leaves_the_public_endpoint_ok(api: Api) -> None:
    healthy(api.dsn)

    statuses = {item["key"]: item["status"] for item in _details(api).json()["checks"]}

    assert statuses["backup"] == "warning"
    assert api.client.get("/api/health").text == "ok"


# Criterion 16.


@pytest.mark.parametrize("token", [None, "wrong-token-0123456789abcdefghijklmn"])
def test_criterion_16_the_details_are_refused_without_the_token(
    api: Api, token: str | None
) -> None:
    response = _details(api, token)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert "worker_heartbeat" not in response.text


def test_criterion_16_without_a_configured_token_the_details_are_always_refused(
    migrated_database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, disk: list[float]
) -> None:
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "storage"))
    with open_api(migrated_database) as started:
        assert _details(started).status_code == 401


def test_criterion_16_the_details_list_each_check_with_value_and_default_threshold(
    api: Api,
) -> None:
    heartbeat(api.dsn, NOW - timedelta(seconds=42))

    body = _details(api).json()

    assert body["status"] == "ok"
    assert [item["key"] for item in body["checks"]] == KEYS
    checks = {item["key"]: item for item in body["checks"]}
    assert checks["worker_heartbeat"] == {
        "key": "worker_heartbeat",
        "status": "ok",
        "value": 42,
        "threshold": 120,
        "unit": "seconds",
    }
    assert checks["database"] == {
        "key": "database",
        "status": "ok",
        "value": "reachable",
        "threshold": "reachable",
        "unit": None,
    }
    assert {key: item["threshold"] for key, item in checks.items()} == {
        "database": "reachable",
        "storage": "reachable",
        "worker_heartbeat": 120,
        "job_queue": 900,
        "email": 0,
        "disk": 20,
        "backup": 93600,
        "verify": 691200,
    }


def test_criterion_16_the_environment_overrides_a_threshold(
    migrated_database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, disk: list[float]
) -> None:
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "storage"))
    monkeypatch.setenv("HEALTH_DETAILS_TOKEN", TOKEN)
    monkeypatch.setenv("HEALTH_WORKER_HEARTBEAT_MAX_AGE", "300")
    with open_api(migrated_database) as started:
        started.clock.now = NOW
        heartbeat(started.dsn, NOW - timedelta(seconds=200))

        checks = {item["key"]: item for item in _details(started).json()["checks"]}

    assert (checks["worker_heartbeat"]["status"], checks["worker_heartbeat"]["threshold"]) == (
        "ok",
        300,
    )


def test_a_report_is_reused_for_a_few_seconds(api: Api) -> None:
    del api.client.app.dependency_overrides[get_cache_seconds]  # type: ignore[attr-defined]
    assert api.client.get("/api/health").text == "fail"  # no worker yet

    healthy(api.dsn)

    assert api.client.get("/api/health").text == "fail"
