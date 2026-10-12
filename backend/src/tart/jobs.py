"""Background jobs: Procrastinate on PostgreSQL (ADR 0004).

    app = create_app(connector_for(database_url))   # api defers, worker runs
    await app.configure_task(SEND_EMAIL).defer_async(kind=…, to=…, language=…, params=…)

The `worker` container runs the jobs; Procrastinate's tables come from the
Alembic chain (`tart migrate`), never from `procrastinate schema --apply`. The
worker passes its services to the jobs through the job context.
"""

import logging
from datetime import UTC, datetime

from procrastinate import App, JobContext, PsycopgConnector
from procrastinate.connector import BaseConnector
from sqlalchemy import delete, make_url
from sqlalchemy.ext.asyncio import AsyncEngine

from tart import rate_limits
from tart.auth import passkeys, sessions
from tart.auth.tables import email_change_code, sign_in_code
from tart.db import create_engine
from tart.email import Mailer

SEND_EMAIL = "send_email"
SWEEP = "sweep"
SWEEP_CRON = "0 * * * *"
"""Hourly, on the hour."""

MAILER = "mailer"
"""The key of the worker's `Mailer` in the job context."""

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


async def sweep(timestamp: int) -> None:
    """The hourly cleanup. Later features add their steps: abandoned uploads, expired drafts."""
    logger.info("hourly sweep (scheduled at %s)", timestamp)
    engine = create_engine()
    try:
        await sweep_database(engine, datetime.now(UTC))
    finally:
        await engine.dispose()


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


def connector_for(database_url: str) -> PsycopgConnector:
    """A Procrastinate connector to the database at `DATABASE_URL` (an asyncpg URL)."""
    conninfo = make_url(database_url).set(drivername="postgresql")
    return PsycopgConnector(conninfo=conninfo.render_as_string(hide_password=False))


def create_app(connector: BaseConnector) -> App:
    app = App(connector=connector)
    app.task(name=SEND_EMAIL, pass_context=True)(send_email)
    app.periodic(cron=SWEEP_CRON)(app.task(name=SWEEP)(sweep))
    return app
