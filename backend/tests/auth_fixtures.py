"""An API client against a migrated database, a controllable clock, and the emails
the API deferred, rendered through the capturing email adapter."""

import asyncio
import json
import re
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

import asyncpg
import pytest
from conftest import ENVIRONMENT, VALID_CONFIG
from fastapi.testclient import TestClient

from tart.api.app import create_app
from tart.api.auth import get_clock
from tart.api.csrf import HEADER
from tart.config import load_configuration
from tart.email import CapturingEmailSender, Mailer
from tart.messages import load_catalogue

BASE_URL = ENVIRONMENT["PUBLIC_BASE_URL"]
START = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


@dataclass
class Clock:
    now: datetime = START

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


@dataclass
class Api:
    client: TestClient
    clock: Clock
    dsn: str
    """The database, as a plain `postgresql://` DSN."""
    _seen: int = field(default=0)

    def request_code(self, email: str, language: str = "it", **extra: object):
        return self.client.post(
            "/api/auth/code", json={"email": email, "language": language, **extra}
        )

    def verify(self, email: str, code: str, language: str = "it", registration=None):
        body: dict[str, object] = {"email": email, "code": code, "language": language}
        if registration is not None:
            body["registration"] = registration
        return self.client.post("/api/auth/code/verify", json=body)

    def query(self, sql: str, *args: object) -> list[asyncpg.Record]:
        async def run() -> list[asyncpg.Record]:
            connection = await asyncpg.connect(self.dsn)
            try:
                return await connection.fetch(sql, *args)
            finally:
                await connection.close()

        return asyncio.run(run())

    def new_emails(self) -> list[EmailMessage]:
        """The emails deferred since the last call, rendered as the worker would."""
        rows = self.query(
            "SELECT id, args FROM procrastinate_jobs WHERE task_name = 'send_email' "
            "AND id > $1 ORDER BY id",
            self._seen,
        )
        if rows:
            self._seen = rows[-1]["id"]
        configuration = load_configuration(
            VALID_CONFIG, {**ENVIRONMENT, "DATABASE_URL": "postgresql+asyncpg://t:t@db/t"}
        )
        sender = CapturingEmailSender()
        mailer = Mailer.from_configuration(configuration, load_catalogue(), sender)
        for row in rows:
            asyncio.run(mailer.send(**json.loads(row["args"])))
        return sender.sent

    def code_from(self, message: EmailMessage) -> str:
        text = message.get_body(("plain",))
        assert text is not None
        match = re.search(r"^(\d{6})$", text.get_content(), re.MULTILINE)
        assert match, text.get_content()
        return match.group(1)

    def sign_in(self, email: str, display_name: str = "Lettrice di prova") -> int:
        """Sign in (registering under `open` if needed); returns the User number."""
        assert self.request_code(email).status_code == 202
        (message,) = self.new_emails()
        response = self.verify(
            email,
            self.code_from(message),
            registration={"display_name": display_name, "age_confirmed": True},
        )
        assert response.json() == {"outcome": "signed_in"}, response.text
        return self.client.get("/api/auth/session").json()["user"]["number"]

    def add_user(self, email: str, *, language: str = "it", suspended: bool = False) -> int:
        (row,) = self.query(
            "INSERT INTO user_account (email, display_name, preferred_language, created_at, "
            "suspended_at, suspension_reason) VALUES ($1, 'Utente di prova', $2, $3, $4, $5) "
            "RETURNING id",
            email,
            language,
            START,
            START if suspended else None,
            "Prova" if suspended else None,
        )
        return row["id"]


def instance_with(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, old: str, new: str) -> None:
    """Point CONFIG_DIR at a copy of the valid configuration with one change to instance.toml."""
    directory = tmp_path / "config"
    shutil.copytree(VALID_CONFIG, directory)
    instance = directory / "instance.toml"
    text = instance.read_text(encoding="utf-8")
    assert old in text
    instance.write_text(text.replace(old, new), encoding="utf-8")
    monkeypatch.setenv("CONFIG_DIR", str(directory))


@contextmanager
def open_api(migrated_database: str) -> Iterator[Api]:
    """The API started on the configuration at CONFIG_DIR, with the clock at `START`."""
    clock = Clock()
    app = create_app()
    app.dependency_overrides[get_clock] = lambda: clock
    with TestClient(app, base_url=BASE_URL, headers={HEADER: "1"}) as client:
        yield Api(client, clock, migrated_database.replace("+asyncpg", ""))
