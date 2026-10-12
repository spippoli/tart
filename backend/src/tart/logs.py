"""Structured logs (Operations and portability spec, 5. Monitoring).

`api` and `worker` write one JSON object per line to stdout:

    {"time": "…Z", "level": "info", "logger": "tart.auth", "message": "signed in", "user_id": 7}

A log line carries the User id where it is relevant, and never an email address, a
sign-in code, a token, or Notice content. Only the fields named in `FIELDS` leave a
record's extras, so a library's context (Procrastinate puts each job's arguments in
its records) stays out; the arguments in Procrastinate's messages are cut, and any
email address left in a message or a traceback is replaced as a last guard.
"""

import json
import logging
import re
from datetime import UTC, datetime

FIELDS = ("user_id", "kind", "check", "job_id", "task")
"""The extras a log line may carry: none of them is personal data in clear."""

REDACTED = "[redacted]"
_EMAIL = re.compile(r"[^\s@<>()\[\]\"',;:]+@[^\s@<>()\[\]\"',;:]+\.[A-Za-z]{2,}")


def _job_message(message: str, job: dict[str, object]) -> str:
    """Procrastinate names a job by its call, `task[id](arguments)`: keep `task[id]`."""
    call = job.get("call_string")
    if isinstance(call, str):
        return message.replace(call, f"{job.get('task_name')}[{job.get('id')}]")
    return message


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        entry: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
        }
        job = getattr(record, "job", None)
        if isinstance(job, dict):
            message = _job_message(message, job)
            entry["job_id"], entry["task"] = job.get("id"), job.get("task_name")
        entry["message"] = message
        for name in FIELDS:
            if name in record.__dict__:
                entry[name] = record.__dict__[name]
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return _EMAIL.sub(REDACTED, json.dumps(entry, ensure_ascii=False, default=str))


def logging_config(level: str = "INFO") -> dict[str, object]:
    """The `logging.config.dictConfig` of `api` and `worker`: JSON on stdout for every
    logger, Uvicorn's included. Uvicorn's access log stays off: Caddy keeps the access log."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"json": {"()": JsonFormatter}},
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            }
        },
        "root": {"handlers": ["stdout"], "level": level},
        "loggers": {
            "uvicorn": {"handlers": [], "propagate": True},
            "uvicorn.error": {"handlers": [], "propagate": True},
            "uvicorn.access": {"handlers": [], "propagate": False},
            # The revision check at startup would log Alembic's plugin set-up.
            "alembic": {"level": "WARNING"},
        },
    }
