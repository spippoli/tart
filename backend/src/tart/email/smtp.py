"""The SMTP adapter of the email port, configured through the environment (ADR 0004).

A generic adapter for any SMTP server: the Operator's provider in production,
Mailpit in development (`SMTP_HOST=mailpit`, `SMTP_PORT=1025`, `SMTP_SECURITY=none`).
"""

import asyncio
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Literal

from tart.config.environment import Environment

TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class SmtpEmailSender:
    host: str
    port: int
    security: Literal["starttls", "tls", "none"]
    username: str | None = None
    password: str | None = None

    @classmethod
    def from_environment(cls, environment: Environment) -> SmtpEmailSender:
        password = environment.SMTP_PASSWORD
        return cls(
            host=environment.SMTP_HOST,
            port=environment.SMTP_PORT,
            security=environment.SMTP_SECURITY,
            username=environment.SMTP_USERNAME,
            password=password.get_secret_value() if password else None,
        )

    async def send(self, message: EmailMessage) -> None:
        # smtplib blocks; one connection per message keeps the adapter stateless.
        await asyncio.to_thread(self._send, message)

    def _send(self, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        if self.security == "tls":
            client = smtplib.SMTP_SSL(
                self.host, self.port, timeout=TIMEOUT_SECONDS, context=context
            )
        else:
            client = smtplib.SMTP(self.host, self.port, timeout=TIMEOUT_SECONDS)
        with client:
            if self.security == "starttls":
                client.starttls(context=context)
            if self.username:
                client.login(self.username, self.password or "")
            client.send_message(message)
