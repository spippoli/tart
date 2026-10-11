"""The public subset of the Instance configuration, which the frontend reads and caches.

It carries what the shell and the forms need from the configuration directory and
nothing from the environment: no secret and no infrastructure wiring.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from tart.config.loader import Instance

# Lists rather than tuples: the generated TypeScript client reads them as `number[]`.
Coordinates = Annotated[list[float], Field(min_length=2, max_length=2)]


class Logo(BaseModel):
    light: str
    """SVG source."""
    dark: str
    alt: str


class Accent(BaseModel):
    light: str
    dark: str


class Identity(BaseModel):
    name: str
    description: str
    logo: Logo
    favicon: str
    """SVG source."""
    accent: Accent


class Contacts(BaseModel):
    general: str | None
    dsa: str
    dsa_languages: list[str]
    privacy: str


class Languages(BaseModel):
    content: str
    ui: list[str]
    """The enabled UI languages; the first one is the default."""


class DefaultView(BaseModel):
    center: Coordinates
    """`[longitude, latitude]`."""
    zoom: float


class Geography(BaseModel):
    country: str
    place_name: str
    time_zone: str
    default_view: DefaultView
    bounds: Annotated[list[float], Field(min_length=4, max_length=4)]
    """The boundary's bounding box: west, south, east, north."""


class Attribution(BaseModel):
    text: str
    url: str


class VocabularyEntry(BaseModel):
    key: str
    label: dict[str, str]
    description: dict[str, str] | None
    retired: bool


class Vocabularies(BaseModel):
    """Each in display order; retired entries stay, for display on existing records."""

    expression_types: list[VocabularyEntry]
    surface_types: list[VocabularyEntry]
    decision_reasons: list[VocabularyEntry]
    """The configured reasons, then the platform's `duplicate`."""
    notice_reasons: list[VocabularyEntry]


class Licenses(BaseModel):
    data: str
    files: list[str]
    """Allowed file licences, in the order of the choice; the first one is the default."""
    data_attribution: str | None


class Texts(BaseModel):
    """The Operator texts, Markdown in the Content language."""

    about: str | None
    editorial_guidelines: str | None
    contribution_policy: str | None
    terms: str
    privacy: str


class PublicConfiguration(BaseModel):
    identity: Identity
    operator_name: str
    contacts: Contacts
    languages: Languages
    geography: Geography
    map_attribution: list[Attribution]
    vocabularies: Vocabularies
    registration: Literal["open", "invite", "closed"]
    licenses: Licenses
    terms_version: int
    texts: Texts


def public_configuration(instance: Instance) -> PublicConfiguration:
    settings = instance.settings
    identity = settings.identity
    return PublicConfiguration(
        identity=Identity(
            name=identity.name,
            description=identity.description,
            logo=Logo(
                light=instance.identity.logo_light,
                dark=instance.identity.logo_dark,
                alt=identity.logo.alt,
            ),
            favicon=instance.identity.favicon,
            accent=Accent(light=identity.accent.light, dark=identity.accent.dark),
        ),
        operator_name=settings.operator.name,
        contacts=Contacts.model_validate(settings.contacts.model_dump()),
        languages=Languages.model_validate(settings.languages.model_dump()),
        geography=Geography(
            country=settings.geography.country,
            place_name=settings.geography.place_name,
            time_zone=settings.geography.time_zone,
            default_view=DefaultView.model_validate(settings.geography.default_view.model_dump()),
            bounds=list(instance.bounds),
        ),
        map_attribution=[
            Attribution.model_validate(entry.model_dump()) for entry in settings.map.attribution
        ],
        vocabularies=Vocabularies.model_validate(
            {
                name: [entry.model_dump() for entry in entries]
                for name, entries in instance.vocabularies.items()
            }
        ),
        registration=settings.community.registration,
        licenses=Licenses.model_validate(settings.licenses.model_dump()),
        terms_version=settings.terms.version,
        texts=Texts.model_validate(dict(instance.texts)),
    )
