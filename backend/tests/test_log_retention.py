"""Log retention (Operations and portability spec, 5. Monitoring, Logs), checked over the
shipped files: every service of the production Compose file logs into the host's
journal, Caddy's access log is on, and the journal settings given to the Operator keep
no line older than 14 days and at most 200 MB. The journal's deletion by time is
systemd's own and is not exercised here."""

import json
import os
import subprocess
from pathlib import Path

from test_caddy_uploads import CADDY_IMAGE

DEPLOY = Path(__file__).parents[2] / "deploy"


def _compose_config() -> dict:
    result = subprocess.run(
        ["docker", "compose", "-f", str(DEPLOY / "compose.yaml"), "config", "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "TART_VERSION": "0.0.0", "POSTGRES_PASSWORD": "x"},
    )
    return json.loads(result.stdout)


# Criterion 19, retention and size.


def test_criterion_19_every_service_logs_into_the_host_journal() -> None:
    services = _compose_config()["services"]

    assert set(services) == {"caddy", "frontend", "api", "worker", "db"}
    assert all(service["logging"] == {"driver": "journald"} for service in services.values())


def test_criterion_19_the_journal_settings_keep_14_days_and_200_mb() -> None:
    compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")

    settings = [line.strip("# ").strip() for line in compose.splitlines() if "=" in line]
    for setting in ("MaxFileSec=1day", "MaxRetentionSec=13day", "SystemMaxUse=200M"):
        assert setting in settings


def test_criterion_19_caddy_keeps_an_access_log() -> None:
    adapted = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--volume",
            f"{DEPLOY / 'Caddyfile'}:/etc/caddy/Caddyfile:ro",
            CADDY_IMAGE,
            "caddy",
            "adapt",
            "--config",
            "/etc/caddy/Caddyfile",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    config = json.loads(adapted.stdout)
    (server,) = config["apps"]["http"]["servers"].values()
    assert "logs" in server
    # Written to stderr, so into the journal, never to a file of its own.
    writers = [log.get("writer") for log in config.get("logging", {}).get("logs", {}).values()]
    assert all(writer is None or writer["output"] == "stderr" for writer in writers)
