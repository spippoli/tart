"""Entry point of the `worker` container.

A placeholder that idles until stopped; the Procrastinate worker replaces it
with the ticket "Worker, email port, and SMTP adapter".
"""

import asyncio
import signal
import sys

from tart.config import ConfigurationError
from tart.migrations import RevisionMismatchError
from tart.startup import start


def main() -> None:
    # Refuse to start on an invalid configuration or on a database the code does not
    # match; never migrate here (ADR 0020).
    try:
        asyncio.run(start())
    except (ConfigurationError, RevisionMismatchError) as error:
        sys.exit(f"worker: {error}")

    stop_signals = {signal.SIGINT, signal.SIGTERM}
    # Block first so the signals queue for sigwait instead of their default action,
    # which the kernel ignores for PID 1 in a container.
    signal.pthread_sigmask(signal.SIG_BLOCK, stop_signals)
    signal.sigwait(stop_signals)


if __name__ == "__main__":
    main()
