"""The SMTP adapter of the email port, against Mailpit (Foundations spec, 2. Email)."""

import asyncio
import json
import urllib.request
from collections.abc import Iterator
from email.headerregistry import Address

import pytest
from conftest import wait_for_http
from testcontainers.core.container import DockerContainer

from tart.email import RenderedEmail, compose
from tart.email.smtp import SmtpEmailSender

# Same image as the `mailpit` service in deploy/compose.dev.yaml; keep the two in step.
MAILPIT_IMAGE = "axllent/mailpit:v1.31.5"


@pytest.fixture(scope="module")
def mailpit() -> Iterator[tuple[str, int, str]]:
    """The SMTP host and port of a Mailpit server, and its API URL."""
    container = DockerContainer(MAILPIT_IMAGE).with_exposed_ports(1025, 8025)
    with container:
        host = container.get_container_host_ip()
        api = f"http://{host}:{container.get_exposed_port(8025)}/api/v1"
        wait_for_http(f"{api}/messages")
        yield host, int(container.get_exposed_port(1025)), api


def _get(url: str) -> dict:
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def test_the_smtp_adapter_delivers_a_multipart_message(mailpit: tuple[str, int, str]) -> None:
    host, port, api = mailpit
    rendered = RenderedEmail(
        language="it",
        subject="[Archivio di prova] Messaggio di prova",
        text="Un messaggio di prova, su una scheda fittizia.",
        html='<!DOCTYPE html>\n<html lang="it"><body><p>Un messaggio di prova.</p></body></html>',
    )
    message = compose(
        rendered,
        sender=Address("Archivio di prova", "archive", "example.org"),
        to="person@example.org",
        reply_to="dsa@example.org",
    )

    asyncio.run(SmtpEmailSender(host=host, port=port, security="none").send(message))

    (summary,) = _get(f"{api}/messages")["messages"]
    stored = _get(f"{api}/message/{summary['ID']}")
    assert stored["From"] == {"Name": "Archivio di prova", "Address": "archive@example.org"}
    assert [to["Address"] for to in stored["To"]] == ["person@example.org"]
    assert [reply["Address"] for reply in stored["ReplyTo"]] == ["dsa@example.org"]
    assert stored["Subject"] == "[Archivio di prova] Messaggio di prova"
    assert stored["Text"].strip() == "Un messaggio di prova, su una scheda fittizia."
    assert "<p>Un messaggio di prova.</p>" in stored["HTML"]


def test_an_unreachable_server_raises() -> None:
    sender = SmtpEmailSender(host="127.0.0.1", port=9, security="none")
    message = compose(
        RenderedEmail("it", "s", "t", "<p>t</p>"),
        sender=Address("A", "a", "example.org"),
        to="b@example.org",
    )

    with pytest.raises(OSError):
        asyncio.run(sender.send(message))
