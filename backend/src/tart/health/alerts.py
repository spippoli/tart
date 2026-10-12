"""Alerting (Operations and portability spec, 5. Monitoring): email the Operator.

Every minute the `worker` runs the checks and emails `OPERATOR_ALERT_EMAIL` about
each failing check it has not emailed about in the last day. The Operator is not a
User: the email is in the Instance's default UI language, with the check key, value,
and threshold untranslated, exactly as in `/api/health/details`, and the time in
the Instance time zone. The primary channel stays the external monitor polling
`/api/health`; this is the reinforcement.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as upsert
from sqlalchemy.ext.asyncio import AsyncEngine

from tart.email import Mailer
from tart.health import Check, Report, Status
from tart.health.tables import operator_alert

OPERATOR_ALERT_EMAIL = "operator_alert"
"""The email kind."""
ALERT_INTERVAL = timedelta(days=1)
"""At most one email per check in this interval."""

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Alerting:
    address: str | None
    """`OPERATOR_ALERT_EMAIL`; without it, nothing is sent."""
    time_zone: ZoneInfo


def _shown(value: object) -> str:
    return "-" if value is None else str(value)


def _with_unit(value: object, check: Check) -> str:
    shown = _shown(value)
    return f"{shown} {check.unit}" if check.unit and value is not None else shown


async def _due(engine: AsyncEngine, failing: list[Check], now: datetime) -> list[Check]:
    """The failing checks not emailed about since `now - ALERT_INTERVAL`."""
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(operator_alert.c.check_key).where(
                operator_alert.c.check_key.in_([check.key for check in failing]),
                operator_alert.c.sent_at > now - ALERT_INTERVAL,
            )
        )
        recent = set(rows.scalars())
    return [check for check in failing if check.key not in recent]


async def _mark_sent(engine: AsyncEngine, check: Check, now: datetime) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            upsert(operator_alert)
            .values(check_key=check.key, sent_at=now)
            .on_conflict_do_update(
                index_elements=[operator_alert.c.check_key], set_={"sent_at": now}
            )
        )


async def send_alerts(
    engine: AsyncEngine, mailer: Mailer, alerting: Alerting, report: Report, now: datetime
) -> list[str]:
    """Email the Operator about each failing check that is due; returns their keys.

    A check whose email fails is retried on the next run.
    """
    failing = [check for check in report.checks if check.status is Status.FAIL]
    if alerting.address is None or not failing:
        return []
    sent = []
    for check in await _due(engine, failing, now):
        params = {
            "check": check.key,
            "value": _with_unit(check.value, check),
            "threshold": _with_unit(check.threshold, check),
            "time": f"{now.astimezone(alerting.time_zone):%Y-%m-%d %H:%M} ({alerting.time_zone})",
        }
        try:
            await mailer.send(
                kind=OPERATOR_ALERT_EMAIL,
                to=alerting.address,
                language=mailer.ui_languages[0],
                params=params,
            )
        except Exception as error:  # the next run tries again
            logger.error(
                "the alert email about %s could not be sent: %s",
                check.key,
                type(error).__name__,
                extra={"check": check.key},
            )
            continue
        await _mark_sent(engine, check, now)
        logger.warning(
            "Operator alerted: check %s is failing", check.key, extra={"check": check.key}
        )
        sent.append(check.key)
    return sent
