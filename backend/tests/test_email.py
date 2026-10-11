"""Foundations spec, 2. Email: rendering in the recipient's language.

The catalogue under `fixtures/messages` holds one fictional email kind,
`record_update`, beside the platform's subject format; the Notifications spec
adds the real kinds to the shipped catalogue.
"""

import asyncio
from email.headerregistry import Address
from email.message import EmailMessage
from pathlib import Path

import pytest
from conftest import ENVIRONMENT, VALID_CONFIG

from tart.config import load_configuration
from tart.email import CapturingEmailSender, Mailer
from tart.messages import load_catalogue

CATALOGUE = load_catalogue(Path(__file__).parent / "fixtures" / "messages")
ARCHIVE_NAME = "Archivio di prova dell'arte urbana"
PARAMS = {"title": "Murale fittizio <senza nome>", "url": "https://archive.example.org/it/x"}


def _mailer(ui_languages: tuple[str, ...] = ("it", "en")) -> Mailer:
    return Mailer(
        catalogue=CATALOGUE,
        sender=CapturingEmailSender(),
        from_address=Address(ARCHIVE_NAME, "archive", "example.org"),
        archive_name=ARCHIVE_NAME,
        ui_languages=ui_languages,
    )


def _send(mailer: Mailer, language: str, reply_to: str | None = None) -> EmailMessage:
    asyncio.run(
        mailer.send(
            kind="record_update",
            to="person@example.org",
            language=language,
            params=PARAMS,
            reply_to=reply_to,
        )
    )
    assert isinstance(mailer.sender, CapturingEmailSender)
    (message,) = mailer.sender.sent
    return message


def _parts(message: EmailMessage) -> tuple[str, str]:
    text = message.get_body(("plain",))
    html = message.get_body(("html",))
    assert text is not None and html is not None
    return text.get_content(), html.get_content()


@pytest.mark.parametrize(
    ("language", "subject", "sentence"),
    [
        ("it", "Aggiornamento su", "La scheda «Murale fittizio <senza nome>» è stata aggiornata."),
        ("en", "Update on", "The record “Murale fittizio <senza nome>” has been updated."),
    ],
)
def test_criterion_38_an_email_is_rendered_in_the_recipients_preferred_ui_language(
    language: str, subject: str, sentence: str
) -> None:
    message = _send(_mailer(), language)

    assert message["Subject"] == f"[{ARCHIVE_NAME}] {subject} Murale fittizio <senza nome>"
    assert message["Content-Language"] == language
    text, html = _parts(message)
    assert sentence in text
    assert f'<html lang="{language}">' in html
    # Quoted content keeps its own language; the catalogue's wording changes.
    assert "Murale fittizio &lt;senza nome&gt;" in html


def test_criterion_38_a_disabled_preferred_language_falls_back_to_the_default_ui_language() -> None:
    message = _send(_mailer(ui_languages=("it",)), "en")

    assert message["Content-Language"] == "it"
    assert "La scheda" in _parts(message)[0]


def test_criterion_38_the_mailer_takes_the_archive_name_and_languages_from_the_configuration() -> (
    None
):
    configuration = load_configuration(
        VALID_CONFIG, {**ENVIRONMENT, "DATABASE_URL": "postgresql+asyncpg://t:t@db/t"}
    )
    sender = CapturingEmailSender()
    mailer = Mailer.from_configuration(configuration, CATALOGUE, sender)

    message = _send(mailer, "en")

    (sender_address,) = message["From"].addresses
    assert sender_address == Address(ARCHIVE_NAME, "archive", "example.org")
    assert message["Subject"].startswith(f"[{ARCHIVE_NAME}] Update on")


def test_every_email_has_a_plain_text_and_a_minimal_html_part() -> None:
    message = _send(_mailer(), "en")

    assert message.get_content_type() == "multipart/alternative"
    text, html = _parts(message)
    assert "See it here: https://archive.example.org/it/x" in text
    assert html.startswith("<!DOCTYPE html>")
    assert "<p>This is a test message, about a fictional record.</p>" in html
    assert "<img" not in html and "src=" not in html
    assert message["To"] == "person@example.org"


def test_reply_to_is_set_only_when_asked() -> None:
    assert _send(_mailer(), "it")["Reply-To"] is None
    assert _send(_mailer(), "it", reply_to="dsa@example.org")["Reply-To"] == "dsa@example.org"
