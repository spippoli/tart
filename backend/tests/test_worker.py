import signal
import subprocess
import sys
import time
from pathlib import Path

from tart.cli import main as run_cli


def _waiting_for_signal(pid: int) -> bool:
    # Linux: the kernel function the process sleeps in, once it reaches sigwait.
    return "sigtimedwait" in Path(f"/proc/{pid}/wchan").read_text()


def test_worker_exits_cleanly_on_sigterm(database: str) -> None:
    run_cli(["migrate"])
    worker = subprocess.Popen([sys.executable, "-m", "tart.worker"])
    deadline = time.monotonic() + 10
    while not _waiting_for_signal(worker.pid):
        assert worker.poll() is None and time.monotonic() < deadline
        time.sleep(0.01)

    worker.send_signal(signal.SIGTERM)

    assert worker.wait(timeout=5) == 0
