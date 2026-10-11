"""Background jobs: Procrastinate on PostgreSQL (ADR 0004).

    app = create_app(connector_for(database_url))   # api defers, worker runs
    await app.configure_task(SEND_EMAIL).defer_async(kind=…, to=…, language=…, params=…)

The `worker` container runs the jobs; Procrastinate's tables come from the
Alembic chain (`tart migrate`), never from `procrastinate schema --apply`. The
worker passes its services to the jobs through the job context.
"""

import logging

from procrastinate import App, JobContext, PsycopgConnector
from procrastinate.connector import BaseConnector
from sqlalchemy import make_url

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
    """The hourly cleanup. Later features add its steps: expired rate-limit counters,
    abandoned uploads, expired drafts."""
    logger.info("hourly sweep (scheduled at %s)", timestamp)


def connector_for(database_url: str) -> PsycopgConnector:
    """A Procrastinate connector to the database at `DATABASE_URL` (an asyncpg URL)."""
    conninfo = make_url(database_url).set(drivername="postgresql")
    return PsycopgConnector(conninfo=conninfo.render_as_string(hide_password=False))


def create_app(connector: BaseConnector) -> App:
    app = App(connector=connector)
    app.task(name=SEND_EMAIL, pass_context=True)(send_email)
    app.periodic(cron=SWEEP_CRON)(app.task(name=SWEEP)(sweep))
    return app
