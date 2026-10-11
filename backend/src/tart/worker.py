"""Entry point of the `worker` container: the Procrastinate worker (ADR 0004).

    python -m tart.worker

It refuses to start on an invalid configuration or on a database the code does
not match, and never migrates (ADR 0020). It runs until SIGTERM or SIGINT, then
finishes the jobs in progress and exits.
"""

import asyncio
import logging
import sys

from tart.config import ConfigurationError
from tart.email import Mailer
from tart.email.smtp import SmtpEmailSender
from tart.jobs import MAILER, connector_for, create_app
from tart.messages import load_catalogue
from tart.migrations import RevisionMismatchError
from tart.startup import start


async def _run() -> None:
    configuration = await start()
    environment = configuration.environment
    mailer = Mailer.from_configuration(
        configuration, load_catalogue(), SmtpEmailSender.from_environment(environment)
    )
    app = create_app(connector_for(environment.DATABASE_URL.get_secret_value()))
    async with app.open_async():
        await app.run_worker_async(additional_context={MAILER: mailer})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(_run())
    except (ConfigurationError, RevisionMismatchError) as error:
        sys.exit(f"worker: {error}")


if __name__ == "__main__":
    main()
