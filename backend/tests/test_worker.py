import signal
import subprocess
import sys
import time


def test_worker_exits_cleanly_on_sigterm() -> None:
    worker = subprocess.Popen([sys.executable, "-m", "tart.worker"])
    time.sleep(0.5)

    worker.send_signal(signal.SIGTERM)

    assert worker.wait(timeout=5) == 0
