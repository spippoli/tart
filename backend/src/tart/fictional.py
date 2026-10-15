"""The fictional development and test dataset (archive-records spec, Testing Decisions).

    python -m tart.fictional seed [--locations N]

writes into an empty archive, at DATABASE_URL with the configuration at CONFIG_DIR, a
small fictional dataset of Rome that covers the record states the record pages are
tested in: a complete record, untitled, unknown artist, disputed attribution,
approximate location, disappeared, destroyed, and documentation without an image.
`--locations N` adds N generated Locations, each with one to three Artworks, for the
Discovery performance check (10,000 there). Pending, merged, and withdrawn records
come with the Submissions, Merge, and Withdrawal that make them.

Every record is fictional and says so in its own text: no name, title, place, or
date here describes a real artwork, artist, or event. The positions are points in
Rome, inside the boundary of both Rome's configuration and the tests' one
(12.40-12.56 E, 41.85-41.95 N), and say nothing about what is there. Images are drawn here,
then stored through the media pipeline as an upload would be.

Records are written through the archive's write operation, as approval will write
them: approval of a Submission is its only caller once Contribution and moderation
exists, and until then the Submissions and Users of the provenance are the dataset's
own (ADR 0002).
"""

import argparse
import asyncio
import io
import math
import os
import random
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta

from PIL import Image, ImageDraw
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncEngine

from tart.archive import (
    AddItem,
    Area,
    Artist,
    ArtistKind,
    Artwork,
    Attribution,
    Certainty,
    Changeset,
    Condition,
    Create,
    CrewMembership,
    DocumentationItem,
    Geometry,
    GeometryKind,
    HistoryEvent,
    HistoryEventType,
    InstanceRules,
    Kind,
    Location,
    Medium,
    New,
    Operation,
    Period,
    Precision,
    Provenance,
    Qualifier,
    RecordId,
    Revision,
    RightsBasis,
    Series,
    SetField,
    Site,
    Source,
    UncertainDate,
    apply_changeset,
)
from tart.archive_persistence import PostgresArchiveStore, rules_from_instance
from tart.archive_persistence import tables as archive_tables
from tart.auth import operator
from tart.config import ConfigurationError, config_dir
from tart.config.loader import load_configuration
from tart.db import create_engine
from tart.discovery.index import rebuild
from tart.media import quarantine_key, uploads
from tart.media.tables import READY
from tart.storage import Area as StorageArea
from tart.storage import Storage, open_storage

MARK = "fittizi"
"""The stem every record carries in its text: "fittizio", "fittizia", and so on, in
Rome's Content language."""

CONTRIBUTOR = "contributor@fictional.example.org"
MODERATOR = "moderator@fictional.example.org"
LANGUAGE = "it"

_FIRST_SUBMISSION = datetime(2025, 1, 10, 9, 30, tzinfo=UTC)
_BATCH = 200
"""Generated changesets written per transaction."""


class ArchiveNotEmptyError(Exception):
    """The archive already holds records: the dataset goes only into an empty one."""


def _point(longitude: float, latitude: float) -> Geometry:
    return Geometry(GeometryKind.POINT, ((longitude, latitude),))


def _rectangle(west: float, south: float, east: float, north: float) -> Geometry:
    return Geometry(
        GeometryKind.POLYGON,
        ((west, south), (east, south), (east, north), (west, north), (west, south)),
    )


def _year(value: int, qualifier: Qualifier = Qualifier.EXACT) -> UncertainDate:
    return UncertainDate(Precision.YEAR, qualifier, date(value, 1, 1))


def _month(year: int, month: int) -> UncertainDate:
    return UncertainDate(Precision.MONTH, Qualifier.EXACT, date(year, month, 1))


def _day(year: int, month: int, day: int) -> UncertainDate:
    return UncertainDate(Precision.DAY, Qualifier.EXACT, date(year, month, day))


def _event(
    key: str, event_type: HistoryEventType, observed: UncertainDate, **values
) -> HistoryEvent:
    return HistoryEvent(id=New(key), type=event_type, observed_date=observed, **values)


def _image(
    artworks: tuple[New, ...], file: str, observed: UncertainDate, alt_text: str, **values
) -> DocumentationItem:
    return DocumentationItem(
        medium=Medium.IMAGE,
        observed_date=observed,
        artworks=artworks,
        file=file,
        licence="CC-BY-SA-4.0",
        creator_credit="Fotografa fittizia",
        rights_basis=RightsBasis.OWN_WORK,
        alt_text=alt_text,
        **values,
    )


# The pictures of the image Documentation items: flat shapes on a wall, drawn here.
_PICTURES = {
    "cat": ((196, 186, 168), [("ellipse", (520, 380, 1080, 900), (40, 40, 40))]),
    "stencil": ((150, 150, 146), [("rectangle", (640, 420, 960, 780), (20, 20, 20))]),
    "shutter": ((176, 180, 184), [("rectangle", (300, 200, 1300, 1000), (120, 60, 70))]),
}


def _picture(name: str) -> bytes:
    background, shapes = _PICTURES[name]
    image = Image.new("RGB", (1600, 1200), background)
    draw = ImageDraw.Draw(image)
    for row in range(0, 1200, 60):  # courses of a plastered wall
        draw.line((0, row, 1600, row), fill=tuple(c - 12 for c in background), width=2)
    for shape, box, colour in shapes:
        getattr(draw, shape)(box, fill=colour)
    output = io.BytesIO()
    image.save(output, "JPEG", quality=85)
    return output.getvalue()


def matrix(files: dict[str, str]) -> Changeset:
    """The state matrix as one changeset, given the stored upload of each picture."""
    nebbia, collettivo, lupo, ombra = New("nebbia"), New("collettivo"), New("lupo"), New("ombra")
    fanzine, intervista = New("fanzine"), New("intervista")
    deposito, gatti = New("deposito"), New("gatti")
    cortile, saracinesca, sottopasso, muro_di_cinta, facciata = (
        New("cortile"),
        New("saracinesca"),
        New("sottopasso"),
        New("muro-di-cinta"),
        New("facciata"),
    )
    gatto, coperto, senza_titolo, fiore, occhio, mani, onda, scritta = (
        New("gatto"),
        New("coperto"),
        New("senza-titolo"),
        New("fiore"),
        New("occhio"),
        New("mani"),
        New("onda"),
        New("scritta"),
    )
    foto_gatto, foto_stencil, foto_saracinesca, testimonianza, collegamento = (
        New("foto-gatto"),
        New("foto-stencil"),
        New("foto-saracinesca"),
        New("testimonianza"),
        New("collegamento"),
    )
    records = [
        (
            fanzine,
            Source(
                title="Muri che parlano, n. 3",
                author="Redazione immaginaria",
                publication="Fanzine fittizia",
                date=_year(2019),
                url="https://example.org/fittizio/muri-che-parlano-3",
                note="Fonte fittizia, inventata per i dati di prova.",
                language="it",
            ),
        ),
        (
            intervista,
            Source(
                title="Intervista fittizia a Nebbia Finta",
                date=_month(2021, 5),
                note="Fonte fittizia: l'intervista non è mai avvenuta.",
            ),
        ),
        (
            New("quartiere"),
            Area(
                name="Quartiere Immaginario",
                geometry=_rectangle(12.4700, 41.8800, 12.5000, 41.9000),
                description="Area fittizia dei dati di prova.",
            ),
        ),
        (
            New("rione"),
            Area(
                name="Rione di Prova",
                geometry=_rectangle(12.4900, 41.8900, 12.5200, 41.9100),
                description="Area fittizia che si sovrappone al Quartiere Immaginario.",
            ),
        ),
        (
            deposito,
            Site(
                name="Ex deposito dei tram fittizio",
                description="Sito fittizio: un deposito dismesso che non esiste.",
            ),
        ),
        (
            gatti,
            Series(
                name="Gatti di carta",
                description="Serie fittizia di gatti dipinti e a stencil.",
                sources=(fanzine,),
            ),
        ),
        (
            nebbia,
            Artist(
                name="Nebbia Finta",
                kind=ArtistKind.INDIVIDUAL,
                biography="Artista fittizia, inventata per i dati di prova.",
                period=Period(start=_year(2010, Qualifier.CIRCA)),
                aliases=("NF",),
                areas=(New("quartiere"),),
                sources=(intervista,),
            ),
        ),
        (
            collettivo,
            Artist(
                name="Collettivo Vernice Assente",
                kind=ArtistKind.COLLECTIVE,
                biography="Collettivo fittizio.",
                period=Period(start=_year(2015), end=_year(2020)),
            ),
        ),
        (
            lupo,
            Artist(
                name="Lupo Inventato",
                kind=ArtistKind.INDIVIDUAL,
                biography="Artista fittizio, membro di un collettivo fittizio.",
                crew_memberships=(
                    CrewMembership(collettivo, Period(start=_year(2016), end=_year(2019))),
                ),
            ),
        ),
        (
            ombra,
            Artist(
                name="Ombra Supposta",
                kind=ArtistKind.INDIVIDUAL,
                biography="Artista fittizio, di cui nessuna fonte è certa.",
            ),
        ),
        (
            cortile,
            Location(
                geometry=_point(12.4950, 41.8950),
                surface_type="building_wall",
                site=deposito,
                place_description="Muro del cortile dell'ex deposito fittizio",
            ),
        ),
        (
            saracinesca,
            Location(
                geometry=_point(12.4800, 41.8850),
                surface_type="shutter",
                place_description="Saracinesca fittizia di via Inventata 7",
            ),
        ),
        (
            sottopasso,
            Location(
                geometry=_point(12.5100, 41.9050),
                surface_type="building_wall",
                approximate=True,
                uncertainty_radius=150,
                place_description="Muro fittizio vicino a un sottopasso, posizione approssimativa",
            ),
        ),
        (
            muro_di_cinta,
            Location(
                geometry=Geometry(GeometryKind.LINE, ((12.4700, 41.9000), (12.4712, 41.9004))),
                surface_type="building_wall",
                place_description="Muro di cinta fittizio lungo via Immaginaria",
            ),
        ),
        (
            facciata,
            Location(
                geometry=_rectangle(12.4860, 41.8780, 12.4864, 41.8783),
                surface_type="building_wall",
                place_description="Facciata fittizia di un edificio inventato",
            ),
        ),
        # A complete record: title, confirmed Attribution, Series, Site, two Areas, image.
        (
            gatto,
            Artwork(
                location=cortile,
                expression_types=("mural", "stencil"),
                title="Il gatto che legge",
                description="Opera fittizia: un gatto nero legge un giornale fittizio.",
                attributions=(Attribution(nebbia, Certainty.CONFIRMED, citations=(fanzine,)),),
                history_events=(
                    _event(
                        "gatto-creato", HistoryEventType.CREATED, _year(2019), citations=(fanzine,)
                    ),
                    _event(
                        "gatto-integro",
                        HistoryEventType.CONDITION_RECORDED,
                        _day(2024, 4, 12),
                        condition=Condition.INTACT,
                        citations=(foto_gatto,),
                    ),
                ),
                series=(gatti,),
                sources=(intervista,),
            ),
        ),
        # Disappeared: covered by the complete record, on the same Location.
        (
            coperto,
            Artwork(
                location=cortile,
                expression_types=("mural",),
                title="Ritratto fittizio",
                description="Opera fittizia, coperta da un'altra opera fittizia.",
                attributions=(Attribution(lupo, Certainty.PROBABLE),),
                history_events=(
                    _event(
                        "coperto-creato", HistoryEventType.CREATED, _year(2012, Qualifier.BEFORE)
                    ),
                    _event(
                        "coperto-coperto",
                        HistoryEventType.COVERED,
                        _year(2019),
                        covering=gatto,
                        note="Nota fittizia: coperto dal gatto.",
                    ),
                ),
            ),
        ),
        # Untitled, signed with an Alias, now missing: the spec's presentation example.
        (
            senza_titolo,
            Artwork(
                location=saracinesca,
                expression_types=("stencil",),
                description="Opera fittizia senza titolo.",
                attributions=(Attribution(nebbia, Certainty.PROBABLE, alias="NF"),),
                history_events=(
                    _event(
                        "senza-titolo-integro",
                        HistoryEventType.CONDITION_RECORDED,
                        _day(2018, 3, 3),
                        condition=Condition.INTACT,
                    ),
                    _event(
                        "senza-titolo-mancante",
                        HistoryEventType.CONDITION_RECORDED,
                        _year(2019, Qualifier.CIRCA),
                        condition=Condition.MISSING,
                    ),
                ),
                series=(gatti,),
            ),
        ),
        # Destroyed, with the documentation of its disappearance.
        (
            fiore,
            Artwork(
                location=saracinesca,
                expression_types=("stencil",),
                title="Fiore fittizio",
                description="Opera fittizia, distrutta con la sostituzione della saracinesca.",
                history_events=(
                    _event("fiore-creato", HistoryEventType.CREATED, _year(2015, Qualifier.CIRCA)),
                    _event(
                        "fiore-distrutto",
                        HistoryEventType.DESTROYED,
                        _day(2020, 2, 10),
                        citations=(foto_saracinesca,),
                    ),
                ),
            ),
        ),
        # Unknown artist.
        (
            occhio,
            Artwork(
                location=muro_di_cinta,
                expression_types=("stencil",),
                title="Occhio fittizio",
                description="Opera fittizia di autore sconosciuto.",
                history_events=(
                    _event(
                        "occhio-integro",
                        HistoryEventType.CONDITION_RECORDED,
                        _year(2023),
                        condition=Condition.INTACT,
                    ),
                ),
            ),
        ),
        # Disputed attribution: two Artists, each disputed.
        (
            mani,
            Artwork(
                location=muro_di_cinta,
                expression_types=("mural",),
                title="Due mani fittizie",
                description="Opera fittizia di attribuzione contesa.",
                attributions=(
                    Attribution(
                        lupo,
                        Certainty.DISPUTED,
                        note="Nota fittizia: attribuita da un'intervista fittizia.",
                        citations=(intervista,),
                    ),
                    Attribution(
                        ombra,
                        Certainty.DISPUTED,
                        note="Nota fittizia: attribuita da una fanzine fittizia.",
                        citations=(fanzine,),
                    ),
                ),
                history_events=(
                    _event("mani-create", HistoryEventType.CREATED, _year(2016, Qualifier.CIRCA)),
                    _event("mani-deteriorate", HistoryEventType.DETERIORATED, _year(2022)),
                ),
            ),
        ),
        # Approximate location, by a collective, damaged then modified.
        (
            onda,
            Artwork(
                location=sottopasso,
                expression_types=("mural",),
                title="Onda fittizia",
                description="Opera fittizia in una posizione nota solo approssimativamente.",
                attributions=(Attribution(collettivo, Certainty.PROBABLE),),
                history_events=(
                    _event("onda-creata", HistoryEventType.CREATED, _year(2017)),
                    _event("onda-danneggiata", HistoryEventType.DAMAGED, _month(2021, 6)),
                    _event(
                        "onda-modificata", HistoryEventType.MODIFIED, _year(2022, Qualifier.AFTER)
                    ),
                ),
            ),
        ),
        # No image: link and text documentation only, on a polygon Location, and a
        # condition observed at an unknown date.
        (
            scritta,
            Artwork(
                location=facciata,
                expression_types=("mural",),
                title="Scritta fittizia",
                description="Opera fittizia documentata solo da un collegamento e da un testo.",
                history_events=(
                    _event(
                        "scritta-integra",
                        HistoryEventType.CONDITION_RECORDED,
                        UncertainDate.unknown(),
                        condition=Condition.INTACT,
                    ),
                ),
            ),
        ),
        (
            foto_gatto,
            _image(
                (gatto,),
                files["cat"],
                _day(2024, 4, 12),
                "Immagine fittizia: un ovale nero su un muro chiaro.",
            ),
        ),
        (
            foto_stencil,
            _image(
                (senza_titolo,),
                files["stencil"],
                _day(2018, 3, 3),
                "Immagine fittizia: un quadrato nero su una saracinesca grigia.",
            ),
        ),
        (
            foto_saracinesca,
            _image(
                (fiore,),
                files["shutter"],
                _day(2020, 2, 10),
                "Immagine fittizia: una saracinesca nuova, senza l'opera.",
                location=saracinesca,
            ),
        ),
        (
            testimonianza,
            DocumentationItem(
                medium=Medium.TEXT,
                observed_date=_month(2023, 9),
                artworks=(scritta,),
                text="Testimonianza fittizia: la scritta era ancora leggibile.",
                language="it",
            ),
        ),
        (
            collegamento,
            DocumentationItem(
                medium=Medium.LINK,
                observed_date=_year(2023),
                artworks=(scritta,),
                url="https://example.org/fittizio/scritta",
                language="it",
            ),
        ),
    ]
    return tuple(Create(ref, record) for ref, record in records)


def later_revision(artwork: RecordId) -> Changeset:
    """A second Submission on the complete record, so it has more than one Revision."""
    return (
        SetField(
            artwork,
            "description",
            "Opera fittizia: un gatto nero legge un giornale fittizio, firmato in basso.",
        ),
        AddItem(
            artwork,
            "history_events",
            _event(
                "gatto-ancora-integro",
                HistoryEventType.CONDITION_RECORDED,
                _day(2024, 11, 20),
                condition=Condition.INTACT,
            ),
        ),
    )


# Generated Locations: what the Discovery performance check needs, varied enough for
# signs, clusters, and filters to have something to show.
_GENERATED_CONDITIONS = (
    (HistoryEventType.CONDITION_RECORDED, 50),
    (HistoryEventType.DETERIORATED, 10),
    (HistoryEventType.DAMAGED, 5),
    (HistoryEventType.MODIFIED, 5),
    (HistoryEventType.COVERED, 10),
    (HistoryEventType.REMOVED, 5),
    (HistoryEventType.DESTROYED, 15),
)


def _generated_date(rng: random.Random) -> UncertainDate:
    year = rng.randint(2000, 2024)
    match rng.random():
        case roll if roll < 0.05:
            return UncertainDate.unknown()
        case roll if roll < 0.3:
            return _day(year, rng.randint(1, 12), rng.randint(1, 28))
        case roll if roll < 0.5:
            return _month(year, rng.randint(1, 12))
        case roll if roll < 0.9:
            return _year(year, rng.choice((Qualifier.EXACT, Qualifier.EXACT, Qualifier.CIRCA)))
        case _:
            return UncertainDate(Precision.DECADE, Qualifier.CIRCA, date(year // 10 * 10, 1, 1))


def _generated_geometry(rng: random.Random, rules: InstanceRules) -> Geometry:
    """A geometry inside the boundary, denser towards the middle of its extent."""
    positions = [p for polygon in rules.boundary.polygons for p in polygon[0]]
    west, east = min(p[0] for p in positions), max(p[0] for p in positions)
    south, north = min(p[1] for p in positions), max(p[1] for p in positions)
    while True:
        longitude = round(rng.gauss((west + east) / 2, (east - west) / 8), 6)
        latitude = round(rng.gauss((south + north) / 2, (north - south) / 8), 6)
        match rng.random():
            case roll if roll < 0.9:
                geometry = _point(longitude, latitude)
            case roll if roll < 0.95:
                angle = rng.uniform(0, math.pi)
                end = (longitude + 0.0006 * math.cos(angle), latitude + 0.0004 * math.sin(angle))
                geometry = Geometry(GeometryKind.LINE, ((longitude, latitude), end))
            case _:
                geometry = _rectangle(longitude, latitude, longitude + 0.0004, latitude + 0.0003)
        if rules.boundary.covers(geometry):
            return geometry


def generated(rules: InstanceRules, count: int, seed: int = 0) -> Iterator[Changeset]:
    """`count` changesets, each a new Location with one to three Artworks on it."""
    rng = random.Random(seed)
    expression_types = sorted(key for key, retired in rules.expression_types.items() if not retired)
    surface_types = sorted(key for key, retired in rules.surface_types.items() if not retired)
    for number in range(1, count + 1):
        geometry = _generated_geometry(rng, rules)
        location = Location(
            geometry=geometry,
            surface_type=rng.choice(surface_types),
            approximate=geometry.kind is GeometryKind.POINT and rng.random() < 0.1,
            place_description=f"Luogo fittizio generato n. {number}",
        )
        if location.approximate:
            location = replace(location, uncertainty_radius=rng.choice((50, 200)))
        operations: list[Operation] = [Create(New("location"), location)]
        for index in range(rng.choice((1, 1, 1, 2, 3))):
            event_type = rng.choices(*zip(*_GENERATED_CONDITIONS, strict=True))[0]
            condition = (
                Condition.INTACT if event_type is HistoryEventType.CONDITION_RECORDED else None
            )
            types = rng.sample(expression_types, rng.choice((1, 1, 2)))
            operations.append(
                Create(
                    New(f"artwork-{index}"),
                    Artwork(
                        location=New("location"),
                        expression_types=tuple(types),
                        title=None
                        if rng.random() < 0.3
                        else f"Opera fittizia {number}.{index + 1}",
                        description="Opera fittizia generata per la prova di carico.",
                        history_events=(
                            HistoryEvent(
                                New(f"event-{index}"), event_type, _generated_date(rng), condition
                            ),
                        ),
                    ),
                )
            )
        yield tuple(operations)


@dataclass(frozen=True)
class Seeded:
    records: dict[Kind, int]
    """How many records of each kind were written."""
    ids: dict[str, RecordId]
    """The id of each record of the state matrix, by its key in `matrix`."""

    @property
    def complete_artwork(self) -> RecordId:
        return self.ids["gatto"]


def _provenance(number: int, contributor: int, moderator: int) -> Provenance:
    submitted_at = _FIRST_SUBMISSION + timedelta(minutes=number)
    return Provenance(
        submission_id=number,
        submitter_id=contributor,
        moderator_id=moderator,
        submitted_at=submitted_at,
        approved_at=submitted_at + timedelta(days=2),
    )


async def _user(engine: AsyncEngine, email: str, display_name: str, now: datetime) -> int:
    async with engine.begin() as connection:
        user = await operator.find(connection, email)
        if user is None:
            user = await operator.create(connection, email, display_name, LANGUAGE, now)
        return user.id


async def _store_picture(
    engine: AsyncEngine, storage: Storage, user_id: int, data: bytes, cap: int, now: datetime
) -> str:
    """Store the picture as an upload would be, through the media pipeline."""
    async with engine.begin() as connection:
        upload_id = await uploads.create(connection, user_id, now)

    async def chunks():
        yield data

    await storage.put(StorageArea.QUARANTINE, quarantine_key(str(upload_id)), chunks())
    async with engine.begin() as connection:
        await uploads.received(connection, upload_id, len(data))
    await uploads.process_upload(engine, storage, upload_id, cap, now)
    async with engine.connect() as connection:
        upload = await uploads.read(connection, upload_id)
    assert upload is not None and upload.status == READY, upload
    return str(upload_id)


async def seed(
    engine: AsyncEngine,
    storage: Storage,
    rules: InstanceRules,
    cap: int,
    *,
    locations: int = 0,
    now: datetime | None = None,
) -> Seeded:
    """Write the dataset into the empty archive, plus `locations` generated Locations.

    Raises `ArchiveNotEmptyError` when the archive holds any record.
    """
    now = now or datetime.now(UTC)
    async with engine.connect() as connection:
        if await connection.scalar(select(exists().select_from(archive_tables.record))):
            raise ArchiveNotEmptyError(
                "the archive is not empty; the dataset goes only into an empty one"
            )
    contributor = await _user(engine, CONTRIBUTOR, "Contributrice fittizia", now)
    moderator = await _user(engine, MODERATOR, "Moderatore fittizio", now)
    files = {
        name: await _store_picture(engine, storage, contributor, _picture(name), cap, now)
        for name in _PICTURES
    }

    counts = dict.fromkeys(Kind, 0)
    submission = 0

    async def write(changesets: Sequence[Changeset]) -> list[tuple[Revision, ...]]:
        """One Submission per changeset, all in one transaction."""
        nonlocal submission
        written = []
        async with engine.begin() as connection:
            store = PostgresArchiveStore(connection, index=False)
            for changeset in changesets:
                submission += 1
                provenance = _provenance(submission, contributor, moderator)
                written.append(await apply_changeset(store, changeset, provenance, rules))
        return written

    dataset = matrix(files)
    [revisions] = await write([dataset])
    # A changeset of creations only has one Revision per record, in its order.
    ids = {
        create.ref.key: revision.record_id
        for create, revision in zip(dataset, revisions, strict=True)
        if isinstance(create, Create)
    }
    await write([later_revision(ids["gatto"])])
    for create in dataset:
        counts[create.record.KIND] += 1

    batch: list[Changeset] = []
    for changeset in generated(rules, locations):
        batch.append(changeset)
        for create in changeset:
            assert isinstance(create, Create)
            counts[create.record.KIND] += 1
        if len(batch) == _BATCH:
            await write(batch)
            batch = []
    if batch:
        await write(batch)
    # The records were written without refreshing the Discovery index, once for each
    # changeset; it is built once here, from the committed archive.
    await rebuild(engine, rules)
    return Seeded(counts, ids)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tart.fictional",
        description="The fictional development and test dataset. Never run it on a live Instance.",
    )
    commands = parser.add_subparsers(title="commands", metavar="<command>", required=True)
    command = commands.add_parser(
        "seed",
        help="write the fictional dataset into an empty archive",
        description=(
            "Write the fictional dataset into the empty archive at DATABASE_URL, with the "
            "configuration at CONFIG_DIR, and its images into the storage."
        ),
    )
    command.add_argument(
        "--locations",
        type=int,
        default=0,
        metavar="N",
        help="also generate N fictional Locations with their Artworks (10000 for Discovery)",
    )
    return parser


async def _main(locations: int) -> Seeded:
    configuration = load_configuration(config_dir(os.environ), os.environ)
    instance = configuration.instance
    engine = create_engine(configuration.environment.DATABASE_URL.get_secret_value())
    try:
        async with open_storage(configuration.environment) as storage:
            return await seed(
                engine,
                storage,
                rules_from_instance(instance),
                instance.settings.media.public_rendition_max_px,
                locations=locations,
            )
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        seeded = asyncio.run(_main(args.locations))
    except (ConfigurationError, ArchiveNotEmptyError) as error:
        print(error, file=sys.stderr)
        return 1
    written = ", ".join(f"{count} {kind}" for kind, count in seeded.records.items() if count)
    print(f"fictional dataset written: {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
