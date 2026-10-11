"""The `worker` container's process: Procrastinate on PostgreSQL (ADR 0004)."""

import signal
import subprocess
import sys
import time

from conftest import fetch_value

from tart.cli import main as run_cli


def _registered_workers(dsn: str) -> object:
    return fetch_value(dsn, "SELECT count(*) FROM procrastinate_workers")


def test_the_worker_runs_against_the_migrated_queue_and_stops_on_sigterm(database: str) -> None:
    # Also Foundations criterion 1: with a valid configuration and a complete environment
    # (conftest), the worker starts and waits for jobs.
    run_cli(["migrate"])
    worker = subprocess.Popen([sys.executable, "-m", "tart.worker"])
    deadline = time.monotonic() + 20
    while not _registered_workers(database):
        assert worker.poll() is None and time.monotonic() < deadline
        time.sleep(0.1)

    worker.send_signal(signal.SIGTERM)

    assert worker.wait(timeout=10) == 0
    assert _registered_workers(database) == 0
