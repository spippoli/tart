"""The background jobs (ADR 0004), run in memory: the email job and the hourly sweep."""

import asyncio

from procrastinate.testing import InMemoryConnector
from test_email import ARCHIVE_NAME, PARAMS, _mailer

from tart.email import CapturingEmailSender
from tart.jobs import MAILER, SEND_EMAIL, SWEEP, SWEEP_CRON, create_app


def test_criterion_38_the_worker_job_renders_and_sends_the_email() -> None:
    mailer = _mailer()
    app = create_app(InMemoryConnector())

    async def run() -> None:
        async with app.open_async():
            await app.configure_task(SEND_EMAIL).defer_async(
                kind="record_update", to="person@example.org", language="en", params=PARAMS
            )
            await app.run_worker_async(wait=False, additional_context={MAILER: mailer})

    asyncio.run(run())

    assert isinstance(mailer.sender, CapturingEmailSender)
    (message,) = mailer.sender.sent
    assert message["Subject"].startswith(f"[{ARCHIVE_NAME}] Update on")


def test_the_sweep_job_runs_every_hour() -> None:
    app = create_app(InMemoryConnector())

    periodic = [
        (task.task.name, task.cron) for task in app.periodic_registry.periodic_tasks.values()
    ]

    assert periodic == [(SWEEP, SWEEP_CRON)]
    assert SWEEP_CRON == "0 * * * *"
