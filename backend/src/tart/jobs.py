"""Background jobs: Procrastinate on PostgreSQL (ADR 0004).

    app = create_app(connector_for(database_url))   # api defers, worker runs
    await app.configure_task(SEND_EMAIL).defer_async(kind=…, to=…, language=…, params=…)

The `worker` container runs the jobs; Procrastinate's tables come from the
Alembic chain (`tart migrate`), never from `procrastinate schema --apply`. The
worker passes its services to the jobs through the job context.
"""

import logging
import uuid
from datetime import UTC, datetime

from procrastinate import App, JobContext, PsycopgConnector
from procrastinate.connector import BaseConnector
from sqlalchemy import delete, make_url
from sqlalchemy.ext.asyncio import AsyncEngine

from tart import health, rate_limits
from tart.auth import passkeys, sessions
from tart.auth.tables import email_change_code, sign_in_code
from tart.email import Mailer
from tart.health import alerts
from tart.media import uploads
from tart.moderation_persistence import retention
from tart.storage import Storage

SEND_EMAIL = "send_email"
PROCESS_UPLOAD = "process_upload"
SWEEP = "sweep"
SWEEP_CRON = "0 * * * *"
"""Hourly, on the hour."""
HEALTH_ALERTS = "health_alerts"
HEALTH_ALERTS_CRON = "* * * * *"
"""Every minute."""
DELETE_COMPLETED_JOBS = "delete_completed_jobs"
DELETE_COMPLETED_JOBS_CRON = "15 4 * * *"
"""Daily, at 04:15 UTC."""
COMPLETED_JOB_RETENTION_HOURS = 30 * 24
"""Completed jobs are deleted after 30 days; failed ones stay for `tart jobs`."""

MAILER = "mailer"
"""The key of the worker's `Mailer` in the job context."""
ENGINE = "engine"
"""The key of the worker's database engine in the job context."""
STORAGE = "storage"
"""The key of the worker's `Storage` in the job context."""
DRAFT_EXPIRY_DAYS = "draft_expiry_days"
"""The key of `community.draft_expiry_days` in the job context."""
HEALTH = "health"
"""The key of the worker's `health.Settings` in the job context."""
ALERTING = "alerting"
"""The key of the worker's `health.alerts.Alerting` in the job context."""

logger = logging.getLogger(__name__)


async def send_email(
    context: JobContext,
    *,
    kind: str,
    to: str,
    language: str,
    params: dict[str, object],
    reply_to: str | None = None,
) -> None:
    """Render one email kind in `language` (or the Instance default) and send it.

    No retry here: the Notifications spec sets the retry schedules.
    """
    mailer: Mailer = context.additional_context[MAILER]
    await mailer.send(kind=kind, to=to, language=language, params=params, reply_to=reply_to)
    logger.info("email %s sent", kind, extra={"kind": kind})


async def process_upload(context: JobContext, *, upload_id: str, cap: int) -> None:
    """Process one quarantined upload into its original and renditions, capped at `cap` px."""
    services = context.additional_context
    await uploads.process_upload(
        services[ENGINE], services[STORAGE], uuid.UUID(upload_id), cap, datetime.now(UTC)
    )


async def sweep(context: JobContext, timestamp: int) -> None:
    """The hourly cleanup: expired counters, codes, and sessions, abandoned uploads, and the
    retention of contributions (drafts, unanswered Submissions, rejected and retracted ones)."""
    logger.info("hourly sweep (scheduled at %s)", timestamp)
    engine: AsyncEngine = context.additional_context[ENGINE]
    storage: Storage = context.additional_context[STORAGE]
    now = datetime.now(UTC)
    await sweep_database(engine, now)
    await uploads.sweep(engine, storage, now)
    await retention.sweep(engine, storage, now, context.additional_context[DRAFT_EXPIRY_DAYS])


async def sweep_database(engine: AsyncEngine, now: datetime) -> None:
    """Delete expired rate-limit counters (and with them the IP addresses they
    hold), expired one-time and email change codes and passkey challenges, and
    expired sessions."""
    async with engine.begin() as connection:
        await rate_limits.delete_expired(connection, now)
        await connection.execute(delete(sign_in_code).where(sign_in_code.c.expires_at <= now))
        await connection.execute(
            delete(email_change_code).where(email_change_code.c.expires_at <= now)
        )
        await passkeys.delete_expired_challenges(connection, now)
        await sessions.delete_expired(connection, now)


async def health_alerts(context: JobContext, timestamp: int) -> None:
    """Run the checks and email the Operator about the failing ones that are due."""
    services = context.additional_context
    now = datetime.now(UTC)
    report = await health.run_checks(
        health.Services(services[ENGINE], services[STORAGE]), services[HEALTH], now
    )
    await alerts.send_alerts(services[ENGINE], services[MAILER], services[ALERTING], report, now)


async def delete_completed_jobs(context: JobContext, timestamp: int) -> None:
    """Delete the jobs that succeeded more than 30 days ago."""
    await context.app.job_manager.delete_old_jobs(nb_hours=COMPLETED_JOB_RETENTION_HOURS)


def connector_for(database_url: str) -> PsycopgConnector:
    """A Procrastinate connector to the database at `DATABASE_URL` (an asyncpg URL)."""
    conninfo = make_url(database_url).set(drivername="postgresql")
    return PsycopgConnector(conninfo=conninfo.render_as_string(hide_password=False))


def create_app(connector: BaseConnector) -> App:
    app = App(connector=connector)
    app.task(name=SEND_EMAIL, pass_context=True)(send_email)
    app.task(name=PROCESS_UPLOAD, pass_context=True)(process_upload)
    app.periodic(cron=SWEEP_CRON)(app.task(name=SWEEP, pass_context=True)(sweep))
    app.periodic(cron=HEALTH_ALERTS_CRON)(
        app.task(name=HEALTH_ALERTS, pass_context=True)(health_alerts)
    )
    app.periodic(cron=DELETE_COMPLETED_JOBS_CRON)(
        app.task(name=DELETE_COMPLETED_JOBS, pass_context=True)(delete_completed_jobs)
    )
    return app
