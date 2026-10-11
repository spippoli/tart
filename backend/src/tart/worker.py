"""Entry point of the `worker` container.

A placeholder that idles until stopped; the Procrastinate worker replaces it
with the ticket "Worker, email port, and SMTP adapter".
"""

import signal


def main() -> None:
    stop_signals = {signal.SIGINT, signal.SIGTERM}
    # Block first so the signals queue for sigwait instead of their default action,
    # which the kernel ignores for PID 1 in a container.
    signal.pthread_sigmask(signal.SIG_BLOCK, stop_signals)
    signal.sigwait(stop_signals)


if __name__ == "__main__":
    main()
