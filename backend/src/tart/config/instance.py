"""The model of `instance.toml` (Foundations spec, 1. Instance configuration).

Every table forbids unknown keys, and every value has a strict scalar type, so a
typo or a quoted number is an error rather than a silent default. Checks that
need another file (the vocabularies, the texts, the identity files) are in
`tart.config.loader`.
"""

import re
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidationInfo,
    field_validator,
)

from tart.colour import HEX_COLOUR, contrast_ratio
from tart.messages import UI_LANGUAGES

CONFIG_VERSION = 1
"""The configuration shape this release reads; bumped by any release that changes it."""

# Platform UI backgrounds, against which each accent value needs 3:1 (non-text contrast,
# WCAG 1.4.11): the accent is never a text colour (Foundations spec, 4. i18n shell).
LIGHT_BACKGROUND = "#FFFFFF"
DARK_BACKGROUND = "#121212"
ACCENT_MIN_CONTRAST = 3.0

DATA_LICENCES = ("CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "ODbL-1.0")
"""SPDX identifiers an Instance may publish its structured data under (ADR 0012)."""

FILE_LICENCES = ("CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0")
"""SPDX identifiers an Instance may allow for uploaded files (ADR 0012)."""

LOGO_LIGHT = "identity/logo.light.svg"
LOGO_DARK = "identity/logo.dark.svg"
FAVICON = "identity/favicon.svg"
BOUNDARY = "geography/boundary.geojson"

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_LANGUAGE = re.compile(r"^[a-z]{2}$")  # ISO 639-1
_COUNTRY = re.compile(r"^[A-Z]{2}$")  # ISO 3166-1 alpha-2
_URL = re.compile(r"^https?://\S+$")


def _email(value: str) -> str:
    if not _EMAIL.match(value):
        raise ValueError(f"{value!r} is not an email address")
    return value


def _language(value: str) -> str:
    if not _LANGUAGE.match(value):
        raise ValueError(f"{value!r} is not an ISO 639-1 language code")
    return value


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be empty")
    return value


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    duplicated = sorted({value for value in values if values.count(value) > 1})
    if duplicated:
        raise ValueError(f"lists {', '.join(duplicated)} more than once")
    return values


Email = Annotated[StrictStr, AfterValidator(_email)]
Language = Annotated[StrictStr, AfterValidator(_language)]
Text = Annotated[StrictStr, AfterValidator(_not_blank)]


class Table(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Logo(Table):
    light: Literal["identity/logo.light.svg"]
    dark: Literal["identity/logo.dark.svg"]
    alt: Text


class Accent(Table):
    light: StrictStr
    dark: StrictStr

    @field_validator("light", "dark")
    @classmethod
    def _contrasts_with_its_theme(cls, value: str, info: ValidationInfo) -> str:
        if not HEX_COLOUR.match(value):
            raise ValueError(f"{value!r} is not a #RRGGBB colour")
        theme = info.field_name
        background = LIGHT_BACKGROUND if theme == "light" else DARK_BACKGROUND
        ratio = contrast_ratio(value, background)
        if ratio < ACCENT_MIN_CONTRAST:
            raise ValueError(
                f"{value} has a contrast of {ratio:.2f}:1 against the {theme} theme's "
                f"background {background}; it needs at least {ACCENT_MIN_CONTRAST:g}:1"
            )
        return value


class Identity(Table):
    name: Text
    description: Text
    logo: Logo
    favicon: Literal["identity/favicon.svg"]
    accent: Accent


class Operator(Table):
    name: Text


class Contacts(Table):
    general: Email | None = None
    dsa: Email
    dsa_languages: Annotated[tuple[Language, ...], Field(min_length=1), AfterValidator(_unique)]
    privacy: Email


def _platform_ui_language(value: str) -> str:
    if value not in UI_LANGUAGES:
        raise ValueError(
            f"{value!r} is not a UI language of this TART release "
            f"(available: {', '.join(UI_LANGUAGES)})"
        )
    return value


class Languages(Table):
    content: Language
    ui: Annotated[
        tuple[Annotated[StrictStr, AfterValidator(_platform_ui_language)], ...],
        Field(min_length=1),
        AfterValidator(_unique),
    ]

    @property
    def default_ui(self) -> str:
        """The default UI language: the first one listed."""
        return self.ui[0]


class DefaultView(Table):
    center: tuple[
        Annotated[StrictFloat, Field(ge=-180, le=180)],
        Annotated[StrictFloat, Field(ge=-90, le=90)],
    ]
    """`[longitude, latitude]`."""
    zoom: Annotated[StrictFloat, Field(ge=0, le=22)]


class Geography(Table):
    country: StrictStr
    place_name: Text
    time_zone: StrictStr
    boundary: Literal["geography/boundary.geojson"]
    default_view: DefaultView

    @field_validator("country")
    @classmethod
    def _iso_country(cls, value: str) -> str:
        if not _COUNTRY.match(value):
            raise ValueError(f"{value!r} is not an ISO 3166-1 alpha-2 country code")
        return value

    @field_validator("time_zone")
    @classmethod
    def _known_time_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError, ValueError:
            raise ValueError(f"{value!r} is not an IANA time zone") from None
        return value


class Attribution(Table):
    text: Text
    url: StrictStr

    @field_validator("url")
    @classmethod
    def _absolute_url(cls, value: str) -> str:
        if not _URL.match(value):
            raise ValueError(f"{value!r} is not an absolute http(s) URL")
        return value


class Map(Table):
    attribution: Annotated[tuple[Attribution, ...], Field(min_length=1)]


class Community(Table):
    registration: Literal["open", "invite", "closed"]
    min_age: Annotated[StrictInt, Field(ge=1)]
    self_approval: StrictBool = False
    draft_expiry_days: Annotated[StrictInt, Field(ge=1)] = 90


class Media(Table):
    max_upload_mb: Annotated[StrictInt, Field(ge=1)] = 25
    public_rendition_max_px: Annotated[StrictInt, Field(ge=1)]


def _data_licence(value: str) -> str:
    if value not in DATA_LICENCES:
        raise ValueError(f"{value!r} is not one of {', '.join(DATA_LICENCES)}")
    return value


def _file_licence(value: str) -> str:
    if value not in FILE_LICENCES:
        raise ValueError(f"{value!r} is not one of {', '.join(FILE_LICENCES)}")
    return value


class Licenses(Table):
    data: Annotated[StrictStr, AfterValidator(_data_licence)]
    files: Annotated[
        tuple[Annotated[StrictStr, AfterValidator(_file_licence)], ...],
        Field(min_length=1),
        AfterValidator(_unique),
    ]
    data_attribution: Text | None = None

    @property
    def default_file(self) -> str:
        """The default file licence: the first one listed."""
        return self.files[0]


class Terms(Table):
    version: Annotated[StrictInt, Field(ge=1)]


class InstanceFile(Table):
    """`instance.toml`."""

    config_version: StrictInt
    identity: Identity
    operator: Operator
    contacts: Contacts
    languages: Languages
    geography: Geography
    map: Map
    community: Community
    media: Media
    licenses: Licenses
    terms: Terms

    @field_validator("config_version")
    @classmethod
    def _this_release_shape(cls, value: int) -> int:
        if value != CONFIG_VERSION:
            raise ValueError(
                f"is {value}, but this TART release reads version {CONFIG_VERSION}; "
                "update the configuration as the release notes describe"
            )
        return value
