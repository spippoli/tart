"""Health (Operations and portability spec, 5. Monitoring): run the checks.

    report = await run_checks(services, settings, now)
    report.status          # fail when any check fails; a warning leaves it ok
    report.checks          # each with its key, status, value, and threshold

`api` serves the report (`GET /api/health`, `GET /api/health/details`); the `worker`
runs the same checks to email the Operator (`tart.health.alerts`). A check that
cannot be read (an unreachable database, a timeout) fails with no value.
"""

import asyncio
import logging
import shutil
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from tart.config.environment import Environment
from tart.health.tables import BACKUP, VERIFY, operation_success
from tart.storage import Area, Storage

DATABASE = "database"
STORAGE = "storage"
WORKER_HEARTBEAT = "worker_heartbeat"
JOB_QUEUE = "job_queue"
EMAIL = "email"
DISK = "disk"
# BACKUP and VERIFY, from tables: each check is named after the operation it watches.

READINESS = (DATABASE, STORAGE, WORKER_HEARTBEAT)
"""The checks `tart upgrade` waits for (Operations spec, 4. Upgrades)."""

REACHABLE = "reachable"
UNREACHABLE = "unreachable"
NOT_CONFIGURED = "not_configured"
SECONDS = "seconds"
PERCENT = "percent"

CHECK_TIMEOUT = 5.0
"""Seconds before a check that has not answered fails."""
PROBE_AREA = Area.QUARANTINE
PROBE_PREFIX = "health-probe"

logger = logging.getLogger(__name__)


class Status(StrEnum):
    OK = "ok"
    WARNING = "warning"
    FAIL = "fail"


type Value = int | float | str | None


@dataclass(frozen=True)
class Check:
    key: str
    status: Status
    value: Value
    """What was measured, untranslated; `None` when it could not be read."""
    threshold: int | float | str
    unit: str | None = None


@dataclass(frozen=True)
class Report:
    checks: tuple[Check, ...]

    @property
    def status(self) -> Status:
        """`fail` when any check fails; a warning does not change it."""
        if any(check.status is Status.FAIL for check in self.checks):
            return Status.FAIL
        return Status.OK


@dataclass(frozen=True)
class Settings:
    """The thresholds and what the checks look at, read from the environment."""

    disk_path: Path = Path("/")
    backups_configured: bool = False
    worker_heartbeat_max_age: int = 120
    job_queue_max_age: int = 15 * 60
    email_max_failed: int = 0
    disk_min_free_percent: float = 20
    backup_max_age: int = 26 * 3600
    verify_max_age: int = 8 * 24 * 3600

    @classmethod
    def from_environment(cls, environment: Environment) -> Settings:
        return cls(
            disk_path=environment.HEALTH_DISK_PATH,
            backups_configured=environment.RESTIC_REPOSITORY is not None,
            worker_heartbeat_max_age=environment.HEALTH_WORKER_HEARTBEAT_MAX_AGE,
            job_queue_max_age=environment.HEALTH_JOB_QUEUE_MAX_AGE,
            email_max_failed=environment.HEALTH_EMAIL_MAX_FAILED,
            disk_min_free_percent=environment.HEALTH_DISK_MIN_FREE_PERCENT,
            backup_max_age=environment.HEALTH_BACKUP_MAX_AGE,
            verify_max_age=environment.HEALTH_VERIFY_MAX_AGE,
        )


@dataclass(frozen=True)
class Services:
    engine: AsyncEngine
    storage: Storage


def _age_check(key: str, since: datetime | None, now: datetime, max_age: int) -> Check:
    """Healthy when `since` is younger than `max_age` seconds."""
    if since is None:
        return Check(key, Status.FAIL, None, max_age, SECONDS)
    age = int((now - since).total_seconds())
    return Check(key, Status.OK if age < max_age else Status.FAIL, age, max_age, SECONDS)


async def _database(services: Services, settings: Settings, now: datetime) -> Check:
    async with services.engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return Check(DATABASE, Status.OK, REACHABLE, REACHABLE)


async def _storage(services: Services, settings: Settings, now: datetime) -> Check:
    """A probe object is written, read back, and deleted."""
    key = f"{PROBE_PREFIX}/{uuid.uuid4().hex}"
    probe = key.encode()

    async def chunks() -> AsyncIterator[bytes]:
        yield probe

    try:
        await services.storage.put(PROBE_AREA, key, chunks())
        async with services.storage.get(PROBE_AREA, key) as stream:
            read = b"".join([chunk async for chunk in stream])
    finally:
        await services.storage.delete(PROBE_AREA, key)
    if read != probe:
        return Check(STORAGE, Status.FAIL, UNREACHABLE, REACHABLE)
    return Check(STORAGE, Status.OK, REACHABLE, REACHABLE)


async def _worker_heartbeat(services: Services, settings: Settings, now: datetime) -> Check:
    async with services.engine.connect() as connection:
        last = await connection.scalar(
            text("SELECT max(last_heartbeat) FROM procrastinate_workers")
        )
    return _age_check(WORKER_HEARTBEAT, last, now, settings.worker_heartbeat_max_age)


async def _job_queue(services: Services, settings: Settings, now: datetime) -> Check:
    """The oldest job waiting to run, counted from when it became due."""
    async with services.engine.connect() as connection:
        oldest = await connection.scalar(
            text(
                "SELECT min(coalesce(job.scheduled_at, event.at)) FROM procrastinate_jobs job "
                "JOIN procrastinate_events event ON event.job_id = job.id "
                "AND event.type = 'deferred' "
                "WHERE job.status = 'todo' "
                "AND (job.scheduled_at IS NULL OR job.scheduled_at <= :now)"
            ),
            {"now": now},
        )
    if oldest is None:
        return Check(JOB_QUEUE, Status.OK, 0, settings.job_queue_max_age, SECONDS)
    return _age_check(JOB_QUEUE, oldest, now, settings.job_queue_max_age)


async def _email(services: Services, settings: Settings, now: datetime) -> Check:
    """Email jobs that failed for good in the last 24 hours."""
    # Imported here: the jobs module imports the services that import this one.
    from tart.jobs import SEND_EMAIL

    async with services.engine.connect() as connection:
        failed = await connection.scalar(
            text(
                "SELECT count(DISTINCT job.id) FROM procrastinate_jobs job "
                "JOIN procrastinate_events event ON event.job_id = job.id "
                "WHERE job.task_name = :task AND job.status = 'failed' "
                "AND event.type = 'failed' AND event.at > :since"
            ),
            {"task": SEND_EMAIL, "since": now - timedelta(hours=24)},
        )
    status = Status.OK if failed <= settings.email_max_failed else Status.FAIL
    return Check(EMAIL, status, failed, settings.email_max_failed)


async def _disk(services: Services, settings: Settings, now: datetime) -> Check:
    usage = await asyncio.to_thread(shutil.disk_usage, settings.disk_path)
    free = round(usage.free / usage.total * 100, 1)
    status = Status.OK if free > settings.disk_min_free_percent else Status.FAIL
    return Check(DISK, status, free, settings.disk_min_free_percent, PERCENT)


async def _last_success(services: Services, operation: str) -> datetime | None:
    async with services.engine.connect() as connection:
        return await connection.scalar(
            select(operation_success.c.succeeded_at).where(
                operation_success.c.operation == operation
            )
        )


async def _backup(services: Services, settings: Settings, now: datetime) -> Check:
    if not settings.backups_configured:
        return Check(BACKUP, Status.WARNING, NOT_CONFIGURED, settings.backup_max_age, SECONDS)
    last = await _last_success(services, BACKUP)
    return _age_check(BACKUP, last, now, settings.backup_max_age)


async def _verify(services: Services, settings: Settings, now: datetime) -> Check:
    # Without backups there is nothing to verify: the same warning as the backup check.
    if not settings.backups_configured:
        return Check(VERIFY, Status.WARNING, NOT_CONFIGURED, settings.verify_max_age, SECONDS)
    last = await _last_success(services, VERIFY)
    return _age_check(VERIFY, last, now, settings.verify_max_age)


type _Run = Callable[[Services, Settings, datetime], Awaitable[Check]]

_CHECKS: tuple[tuple[str, _Run, str | None], ...] = (
    (DATABASE, _database, None),
    (STORAGE, _storage, None),
    (WORKER_HEARTBEAT, _worker_heartbeat, SECONDS),
    (JOB_QUEUE, _job_queue, SECONDS),
    (EMAIL, _email, None),
    (DISK, _disk, PERCENT),
    (BACKUP, _backup, SECONDS),
    (VERIFY, _verify, SECONDS),
)
"""Each check in report order, with its unit."""


def _threshold(key: str, settings: Settings) -> int | float | str:
    return {
        DATABASE: REACHABLE,
        STORAGE: REACHABLE,
        WORKER_HEARTBEAT: settings.worker_heartbeat_max_age,
        JOB_QUEUE: settings.job_queue_max_age,
        EMAIL: settings.email_max_failed,
        DISK: settings.disk_min_free_percent,
        BACKUP: settings.backup_max_age,
        VERIFY: settings.verify_max_age,
    }[key]


async def _run(
    key: str, run: _Run, unit: str | None, services: Services, settings: Settings, now: datetime
) -> Check:
    try:
        async with asyncio.timeout(CHECK_TIMEOUT):
            return await run(services, settings, now)
    except Exception as error:  # whatever stops a check makes it fail
        logger.warning(
            "health check %s could not run: %s", key, type(error).__name__, extra={"check": key}
        )
        threshold = _threshold(key, settings)
        value = UNREACHABLE if threshold == REACHABLE else None
        return Check(key, Status.FAIL, value, threshold, unit)


async def run_checks(services: Services, settings: Settings, now: datetime) -> Report:
    """Every check, concurrently, in a fixed order."""
    checks = await asyncio.gather(
        *(_run(key, run, unit, services, settings, now) for key, run, unit in _CHECKS)
    )
    return Report(tuple(checks))
