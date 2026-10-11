"""Rules on what Users enter: email addresses and display names (Foundations spec, 2)."""

import re
import unicodedata
from collections.abc import Sequence

from tart.auth import (
    DISPLAY_NAME_CONTROL_CHARACTERS,
    DISPLAY_NAME_LENGTH,
    DISPLAY_NAME_RESERVED,
)
from tart.messages import Catalogue

DISPLAY_NAME_MAX_LENGTH = 40
EMAIL_MAX_LENGTH = 254
PSEUDONYM_KEY = "deleted_user_pseudonym"
"""The catalogue key of the deleted-account Pseudonym, "Deleted user {number}"."""

_EMAIL = re.compile(r"[^@\s<>]+@[^@\s<>]+\.[^@\s<>.]+")


def normalise_email(value: str) -> str | None:
    """The address as stored and compared (trimmed, lower case), or None if it is not one."""
    email = value.strip().lower()
    if len(email) > EMAIL_MAX_LENGTH or not _EMAIL.fullmatch(email):
        return None
    return email


def display_name_problem(
    value: str, catalogue: Catalogue, ui_languages: Sequence[str]
) -> str | None:
    """The error code of a display name, or None if it may be used as entered (trimmed).

    Display names are not unique; one may not read as the Pseudonym of a deleted
    account, with any number, in any enabled UI language.
    """
    name = value.strip()
    if not 1 <= len(name) <= DISPLAY_NAME_MAX_LENGTH:
        return DISPLAY_NAME_LENGTH
    if any(unicodedata.category(character) == "Cc" for character in name):
        return DISPLAY_NAME_CONTROL_CHARACTERS
    for language in ui_languages:
        before, _, after = catalogue.messages[language][PSEUDONYM_KEY].partition("{number}")
        pattern = re.escape(before.casefold()) + r"\s*\d+\s*" + re.escape(after.casefold())
        if re.fullmatch(pattern, " ".join(name.casefold().split())):
            return DISPLAY_NAME_RESERVED
    return None
