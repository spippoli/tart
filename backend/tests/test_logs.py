"""Structured logs (Operations and portability spec, 5. Monitoring, Logs): JSON lines on
stdout carrying the User id where relevant and never an email address, a sign-in code,
or a token. Notice intake logs nothing yet: Rights and legal actions adds it."""

import asyncio
import json
import logging
import logging.config
from collections.abc import Iterator

import pytest
from auth_fixtures import open_api
from procrastinate import App
from procrastinate.testing import InMemoryConnector
from test_health_alerts import _mailer
from test_jobs_admin import ADDRESS, SECRET_CODE, Down

from tart import jobs
from tart.logs import REDACTED, JsonFormatter, logging_config

FORMATTER = JsonFormatter()


def lines(records: list[logging.LogRecord]) -> list[dict[str, object]]:
    return [json.loads(FORMATTER.format(record)) for record in records]


def assert_no_personal_data(records: list[logging.LogRecord], *secrets: str) -> None:
    text = "\n".join(FORMATTER.format(record) for record in records)
    for secret in secrets:
        assert secret not in text


def test_a_log_line_is_one_json_object_with_time_level_logger_and_message() -> None:
    record = logging.LogRecord("tart.test", logging.WARNING, __file__, 1, "%s left", ("one",), None)
    record.user_id = 7
    record.email = ADDRESS  # an extra that is not a log field stays out

    line = FORMATTER.format(record)

    assert "\n" not in line
    entry = json.loads(line)
    assert entry.pop("time").endswith("+00:00")
    assert entry == {"level": "warning", "logger": "tart.test", "message": "one left", "user_id": 7}


def test_an_email_address_in_a_message_or_a_traceback_is_redacted() -> None:
    try:
        raise OSError(f"550 mailbox unavailable: <{ADDRESS}>")
    except OSError:
        record = logging.LogRecord(
            "tart.test", logging.ERROR, __file__, 1, "refused %s", (ADDRESS,), True
        )
        record.exc_info = __import__("sys").exc_info()

    entry = json.loads(FORMATTER.format(record))

    assert entry["message"] == f"refused {REDACTED}"
    assert ADDRESS not in entry["exception"] and REDACTED in entry["exception"]


# Criterion 19.


def _run_email_jobs(sender: object | None) -> None:
    app = App(connector=InMemoryConnector())
    app.task(name=jobs.SEND_EMAIL, pass_context=True)(jobs.send_email)

    async def run() -> None:
        async with app.open_async():
            await app.configure_task(jobs.SEND_EMAIL).defer_async(
                kind="sign_in_code",
                to=ADDRESS,
                language="it",
                params={"code": SECRET_CODE, "minutes": 15},
            )
            await app.run_worker_async(
                wait=False, additional_context={jobs.MAILER: _mailer(sender)}
            )

    asyncio.run(run())


def test_criterion_19_sending_an_email_logs_its_kind_and_no_address_or_code(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        _run_email_jobs(None)

    entries = lines(caplog.records)
    assert {"message": "email sign_in_code sent", "kind": "sign_in_code"}.items() <= next(
        entry for entry in entries if entry["logger"] == "tart.jobs"
    ).items()
    # Procrastinate names the job by its call: only `task[id]` is kept.
    started = next(entry for entry in entries if str(entry["message"]).startswith("Starting job"))
    assert started["message"] == f"Starting job send_email[{started['job_id']}]"
    assert started["task"] == "send_email"
    assert_no_personal_data(caplog.records, ADDRESS, SECRET_CODE)


def test_criterion_19_a_failed_email_logs_no_address_or_code(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        _run_email_jobs(Down())

    assert any(record.exc_info for record in caplog.records)
    assert_no_personal_data(caplog.records, ADDRESS, SECRET_CODE)


def test_criterion_19_sign_in_logs_the_user_id_and_no_address_code_or_token(
    migrated_database: str, caplog: pytest.LogCaptureFixture
) -> None:
    with open_api(migrated_database) as api, caplog.at_level(logging.DEBUG):
        number = api.sign_in("lettrice@example.org")
        api.clock.advance(minutes=10)
        assert api.request_code("lettrice@example.org").status_code == 202
        (message,) = api.new_emails()
        code = api.code_from(message)
        assert api.verify("lettrice@example.org", code).status_code == 200
        token = api.client.cookies.get("tart_session") or ""

    user_id = api.query("SELECT id FROM user_account")[0]["id"]
    signed_in = [
        entry for entry in lines(caplog.records) if entry["logger"] == "tart.auth.built_in"
    ]
    assert [(entry["message"], entry["user_id"]) for entry in signed_in] == [
        ("registered and signed in", user_id),
        ("signed in with a code", user_id),
    ]
    assert number
    assert_no_personal_data(
        caplog.records, "lettrice@example.org", code, *([token] if token else [])
    )


@pytest.fixture
def restored_logging() -> Iterator[None]:
    """Puts back the logging configuration that a test replaces."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    uvicorn = {
        name: (logging.getLogger(name).handlers[:], logging.getLogger(name).propagate)
        for name in ("uvicorn", "uvicorn.error", "uvicorn.access")
    }
    yield
    root.handlers[:] = handlers
    root.setLevel(level)
    for name, (saved, propagate) in uvicorn.items():
        logging.getLogger(name).handlers[:] = saved
        logging.getLogger(name).propagate = propagate


def test_criterion_19_api_and_worker_logs_are_json_lines_on_stdout(
    restored_logging: None, capsys: pytest.CaptureFixture[str]
) -> None:
    logging.config.dictConfig(logging_config())  # here: capsys captures the test body only
    logging.getLogger("uvicorn.error").info("Application startup complete.")
    logging.getLogger("tart.jobs").info("hourly sweep")
    logging.getLogger("uvicorn.access").info("GET /api/health 200")

    out = capsys.readouterr().out.splitlines()

    assert [(entry["logger"], entry["message"]) for entry in map(json.loads, out)] == [
        ("uvicorn.error", "Application startup complete."),
        ("tart.jobs", "hourly sweep"),
    ]
