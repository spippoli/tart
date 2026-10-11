"""Email: render a message from the backend catalogue and send it through a port.

    mailer = Mailer.from_configuration(configuration, sender)
    await mailer.send(kind="sign_in_code", to="…", language="en", params={…})

The `worker` renders every email (Foundations spec, 2. Email; ADR 0008): a plain-text
and a minimal HTML part in the recipient's language, with no remote resource. An
email kind is two catalogue keys, `email_<kind>_subject` (the event, which the
subject wraps as `[<archive name>] <event>`) and `email_<kind>_body`, whose
paragraphs are separated by a blank line. The Notifications spec adds the kinds.

Sending goes through `EmailSender`; `SmtpEmailSender` (`tart.email.smtp`) is the
one adapter, `CapturingEmailSender` keeps the messages for tests.
"""

import html
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from email.headerregistry import Address
from email.message import EmailMessage
from typing import Protocol

from tart.config import Configuration
from tart.messages import Catalogue


class EmailSender(Protocol):
    """The email port: deliver one composed message, or raise."""

    async def send(self, message: EmailMessage) -> None: ...


@dataclass
class CapturingEmailSender:
    """An adapter that delivers nothing and keeps every message, for tests."""

    sent: list[EmailMessage] = field(default_factory=list)

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


def email_language(requested: str, ui_languages: Sequence[str]) -> str:
    """The recipient's language if the Instance still enables it, else its default UI language."""
    return requested if requested in ui_languages else ui_languages[0]


@dataclass(frozen=True)
class RenderedEmail:
    language: str
    subject: str
    text: str
    html: str


def render_email(
    catalogue: Catalogue,
    *,
    kind: str,
    language: str,
    archive_name: str,
    params: Mapping[str, object],
) -> RenderedEmail:
    """One email kind in one language, as a subject, a plain-text part, and an HTML part."""
    event = catalogue.render(language, f"email_{kind}_subject", **params)
    subject = catalogue.render(language, "email_subject", archive_name=archive_name, event=event)
    text = catalogue.render(language, f"email_{kind}_body", **params)
    paragraphs = "\n".join(
        "<p>{}</p>".format(html.escape(paragraph).replace("\n", "<br>\n"))
        for paragraph in text.split("\n\n")
    )
    document = (
        f'<!DOCTYPE html>\n<html lang="{language}">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{html.escape(subject)}</title>\n</head>\n<body>\n{paragraphs}\n</body>\n</html>\n"
    )
    return RenderedEmail(language, subject, text, document)


def compose(
    rendered: RenderedEmail, *, sender: Address, to: str, reply_to: str | None = None
) -> EmailMessage:
    """A multipart/alternative message: the plain text first, then the HTML."""
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    if reply_to:
        message["Reply-To"] = reply_to
    message["Subject"] = rendered.subject
    message.set_content(rendered.text)
    message.add_alternative(rendered.html, subtype="html")
    # After the parts: setting the content clears every Content-* header.
    message["Content-Language"] = rendered.language
    return message


@dataclass(frozen=True)
class Mailer:
    """Renders an email kind for one recipient and sends it."""

    catalogue: Catalogue
    sender: EmailSender
    from_address: Address
    """The From name is the archive name; the address comes from `SMTP_FROM`."""
    archive_name: str
    ui_languages: Sequence[str]
    """The enabled UI languages, default first."""

    @classmethod
    def from_configuration(
        cls, configuration: Configuration, catalogue: Catalogue, sender: EmailSender
    ) -> Mailer:
        settings = configuration.instance.settings
        archive_name = settings.identity.name
        username, _, domain = configuration.environment.SMTP_FROM.rpartition("@")
        return cls(
            catalogue=catalogue,
            sender=sender,
            from_address=Address(archive_name, username, domain),
            archive_name=archive_name,
            ui_languages=settings.languages.ui,
        )

    async def send(
        self,
        *,
        kind: str,
        to: str,
        language: str,
        params: Mapping[str, object],
        reply_to: str | None = None,
    ) -> None:
        """Send `kind` to `to` in `language`, the recipient's preferred UI language or,
        for an address without a User, that of the page they acted from."""
        rendered = render_email(
            self.catalogue,
            kind=kind,
            language=email_language(language, self.ui_languages),
            archive_name=self.archive_name,
            params=params,
        )
        await self.sender.send(
            compose(rendered, sender=self.from_address, to=to, reply_to=reply_to)
        )
