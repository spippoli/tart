"""The fictional development and test dataset (archive-records spec, Testing Decisions).

The seed writes, through the archive's write operation, a dataset that covers the
record states the pages are tested in, every record marked as fictional; and a
generator of Locations for the Discovery performance check.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from archive_fixtures import RULES, Archive
from conftest import VALID_CONFIG
from sqlalchemy import select

from tart.archive import (
    ApprovedEvent,
    Artwork,
    Certainty,
    ConditionGroup,
    DocumentationItem,
    GeometryKind,
    Kind,
    Location,
    Medium,
    Record,
    condition_group,
    derive_condition,
)
from tart.archive_persistence import rules_from_instance
from tart.archive_persistence.tables import record as record_table
from tart.config import load_instance
from tart.db import create_engine
from tart.fictional import MARK, ArchiveNotEmptyError, Seeded, generated, main, seed
from tart.media import Rendition, original_key, rendition_key
from tart.storage import Area as StorageArea
from tart.storage.filesystem import FilesystemStorage

ROME = Path(__file__).parents[3] / "instances" / "rome"
NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


def _seed(url: str, storage_path: Path, rules=RULES, locations: int = 0) -> Seeded:
    async def run() -> Seeded:
        engine = create_engine(url)
        try:
            storage = FilesystemStorage(storage_path)
            return await seed(engine, storage, rules, 2048, locations=locations, now=NOW)
        finally:
            await engine.dispose()

    return asyncio.run(run())


def _records(archive: Archive) -> dict[int, Record]:
    async def ids(store) -> list[int]:
        return list(await store.connection.scalars(select(record_table.c.id)))

    found = {}
    for record_id in archive.read(ids):
        record = archive.get(record_id)
        assert record is not None
        found[record_id] = record
    return found


def _condition(artwork: Artwork):
    approved = datetime(2025, 1, 1, tzinfo=UTC)
    return derive_condition(ApprovedEvent(event, approved) for event in artwork.history_events)


def test_the_dataset_covers_the_record_states(migrated_database: str, tmp_path: Path) -> None:
    seeded = _seed(migrated_database, tmp_path)
    records = _records(Archive(migrated_database))

    assert sum(seeded.records.values()) == len(records)
    assert {record.KIND for record in records.values()} == set(Kind)
    artworks = {i: r for i, r in records.items() if isinstance(r, Artwork)}
    locations = {i: r for i, r in records.items() if isinstance(r, Location)}
    items = [r for r in records.values() if isinstance(r, DocumentationItem)]

    complete = artworks[seeded.complete_artwork]
    assert complete.title and complete.series and complete.sources
    assert [a.certainty for a in complete.attributions] == [Certainty.CONFIRMED]
    assert locations[complete.location].site is not None
    assert _condition(complete).condition.value == "intact"
    assert any(
        item.medium is Medium.IMAGE and seeded.complete_artwork in item.artworks for item in items
    )

    assert any(artwork.title is None for artwork in artworks.values())
    assert any(not artwork.attributions for artwork in artworks.values())
    assert any(
        artwork.attributions
        and all(a.certainty is Certainty.DISPUTED for a in artwork.attributions)
        for artwork in artworks.values()
    )
    assert any(locations[artwork.location].approximate for artwork in artworks.values())
    conditions = [_condition(artwork).condition.value for artwork in artworks.values()]
    assert {"covered", "missing", "destroyed"} <= set(conditions)
    assert any(
        condition_group(_condition(artwork).condition) is ConditionGroup.DISAPPEARED
        for artwork in artworks.values()
    )
    with_image = {
        artwork for item in items if item.medium is Medium.IMAGE for artwork in item.artworks
    }
    documented = {artwork for item in items for artwork in item.artworks}
    assert documented - with_image, "an Artwork documented without an image"
    assert {location.geometry.kind for location in locations.values()} == set(GeometryKind)


def test_every_record_is_marked_as_fictional(migrated_database: str, tmp_path: Path) -> None:
    _seed(migrated_database, tmp_path, locations=5)

    for record in _records(Archive(migrated_database)).values():
        assert MARK in repr(record), record


def test_the_complete_record_has_a_later_revision(migrated_database: str, tmp_path: Path) -> None:
    seeded = _seed(migrated_database, tmp_path)

    revisions = Archive(migrated_database).read(
        lambda store: store.revisions_of(seeded.complete_artwork)
    )
    assert len(revisions) == 2
    assert revisions[0].provenance.approved_at < revisions[1].provenance.approved_at


def test_the_images_are_stored_through_the_media_pipeline(
    migrated_database: str, tmp_path: Path
) -> None:
    _seed(migrated_database, tmp_path)
    images = [
        record
        for record in _records(Archive(migrated_database)).values()
        if isinstance(record, DocumentationItem) and record.medium is Medium.IMAGE
    ]

    assert images
    for item in images:
        assert item.file is not None
        keys = [original_key(item.file), *(rendition_key(item.file, r) for r in Rendition)]
        for key in keys:
            assert (tmp_path / StorageArea.PERMANENT.value / key).is_file(), key


def test_the_dataset_goes_only_into_an_empty_archive(
    migrated_database: str, tmp_path: Path
) -> None:
    _seed(migrated_database, tmp_path)

    with pytest.raises(ArchiveNotEmptyError):
        _seed(migrated_database, tmp_path)


def test_rome_accepts_the_dataset(migrated_database: str, tmp_path: Path) -> None:
    rome = rules_from_instance(load_instance(ROME))

    seeded = _seed(migrated_database, tmp_path, rules=rome, locations=20)

    assert seeded.records[Kind.LOCATION] == 5 + 20


@pytest.mark.parametrize("directory", [VALID_CONFIG, ROME], ids=["tests", "rome"])
def test_generated_locations_lie_inside_the_boundary(directory: Path) -> None:
    rules = rules_from_instance(load_instance(directory))

    changesets = list(generated(rules, 300))

    assert len(changesets) == 300
    locations = [
        op.record for changeset in changesets for op in changeset if op.ref.key == "location"
    ]
    assert len(locations) == 300
    assert all(rules.boundary.covers(location.geometry) for location in locations)
    assert {location.geometry.kind for location in locations} == set(GeometryKind)
    # The same seed gives the same Locations, so a performance run can be repeated.
    assert list(generated(rules, 300)) == changesets


def test_the_command_seeds_the_archive_once(
    migrated_database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))

    assert main(["seed", "--locations", "3"]) == 0
    assert "fictional dataset written" in capsys.readouterr().out
    assert main(["seed"]) == 1
    assert "not empty" in capsys.readouterr().err
