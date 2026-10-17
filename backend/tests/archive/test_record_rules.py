"""The rules each record kind satisfies on its own (archive-records spec, Artwork to
Documentation item). Every record here is fictional.
"""

import inspect
import typing
from dataclasses import fields, replace
from datetime import date

import pytest
from archive_fixtures import OBSERVED, RULES, artwork, image, location, point, square

from tart.archive import (
    AddItem,
    ArchiveRuleViolation,
    ArchiveStore,
    Area,
    Artist,
    ArtistKind,
    Attribution,
    Certainty,
    ChangeItem,
    Create,
    DocumentationItem,
    Geometry,
    GeometryKind,
    LocationTitle,
    Medium,
    Operation,
    Precision,
    Qualifier,
    Record,
    RemoveItem,
    RightsBasis,
    Series,
    SetField,
    Site,
    Source,
    UncertainDate,
    location_title,
)
from tart.archive.records import RECORD_TYPES
from tart.archive.rules import check_record

SUBMITTED_ON = date(2026, 9, 1)


def _check(record: Record, before: Record | None = None) -> None:
    check_record(record, before, RULES, SUBMITTED_ON)


def _violation(record: Record, before: Record | None = None) -> str:
    with pytest.raises(ArchiveRuleViolation) as raised:
        _check(record, before)
    return raised.value.code


# Criterion 4: no operation deletes an Artwork or a Location.


def test_criterion_4_the_changeset_has_no_operation_that_deletes_a_record() -> None:
    assert set(typing.get_args(Operation.__value__)) == {
        Create,
        SetField,
        AddItem,
        ChangeItem,
        RemoveItem,
    }
    # RemoveItem removes an item of a collection, never a record.
    assert [field.name for field in fields(RemoveItem)] == ["target", "collection", "key"]


def test_criterion_4_the_archive_port_cannot_delete() -> None:
    methods = {name for name, _ in inspect.getmembers(ArchiveStore) if not name.startswith("_")}

    assert methods == {
        "allocate_id",
        "allocate_history_event_id",
        "get",
        "save",
        "add_revision",
        "public_records",
        "members_of",
        "artworks_signed_with",
        "documentation_items_of",
        "watch",
        "settle",
    }


# Criterion 15: no authorisation, legality, image of the person, or User link.


def test_criterion_15_no_record_kind_has_a_field_for_authorisation_or_legality() -> None:
    forbidden = ("authori", "legal", "permi", "illegal", "lawful", "commission")
    for record_type in RECORD_TYPES.values():
        for name in record_type.field_names():
            assert not any(word in name for word in forbidden), (record_type, name)


def test_criterion_15_an_artist_has_no_image_of_the_person_and_no_user() -> None:
    names = Artist.field_names()

    assert names == (
        "name",
        "kind",
        "biography",
        "period",
        "aliases",
        "areas",
        "crew_memberships",
        "sources",
    )


# Location (criteria 10, 11, 48).


def test_criterion_10_a_location_outside_the_instance_boundary_is_rejected() -> None:
    assert _violation(location(geometry=point(12.30, 41.90))) == "location.outside_boundary"


def test_criterion_10_a_line_leaving_the_boundary_is_rejected() -> None:
    line = Geometry(GeometryKind.LINE, ((12.50, 41.90), (12.60, 41.90)))

    assert _violation(location(geometry=line)) == "location.outside_boundary"


def test_criterion_10_points_lines_and_polygons_inside_the_boundary_are_accepted() -> None:
    _check(location(geometry=point()))
    _check(location(geometry=Geometry(GeometryKind.LINE, ((12.48, 41.89), (12.49, 41.89)))))
    _check(location(geometry=square(12.48, 41.89, 12.481, 41.891)))


def test_criterion_11_an_uncertainty_radius_is_accepted_on_an_approximate_point() -> None:
    _check(location(approximate=True, uncertainty_radius=40))


@pytest.mark.parametrize(
    "values",
    [
        {"approximate": False, "uncertainty_radius": 40},
        {
            "approximate": True,
            "uncertainty_radius": 40,
            "geometry": Geometry(GeometryKind.LINE, ((12.48, 41.89), (12.49, 41.89))),
        },
        {
            "approximate": True,
            "uncertainty_radius": 40,
            "geometry": square(12.48, 41.89, 12.481, 41.891),
        },
    ],
)
def test_criterion_11_an_uncertainty_radius_is_rejected_elsewhere(values: dict) -> None:
    assert _violation(location(**values)) == "location.radius_requires_approximate_point"


def test_approximate_applies_to_every_geometry_kind() -> None:
    _check(location(approximate=True, geometry=square(12.48, 41.89, 12.481, 41.891)))


def test_criterion_48_a_place_description_longer_than_200_characters_is_rejected() -> None:
    _check(location(place_description="x" * 200))

    assert (
        _violation(location(place_description="x" * 201)) == "location.place_description_too_long"
    )


def test_a_place_description_is_one_line() -> None:
    assert (
        _violation(location(place_description="Shutter at no. 12\nleft"))
        == "location.place_description_not_one_line"
    )


def test_criterion_48_a_location_title_is_its_place_description_first() -> None:
    record = location(place_description="Shutter at no. 12, left of the entrance")

    assert location_title(record, "Fictional hall", ["Fictional rione"]) == LocationTitle(
        place_description="Shutter at no. 12, left of the entrance"
    )


def test_criterion_48_without_a_place_description_the_title_is_surface_type_and_site() -> None:
    record = location(surface_type="shutter")

    assert location_title(record, "Fictional hall", ["Fictional rione"]) == LocationTitle(
        surface_type="shutter", place="Fictional hall"
    )
    assert location_title(record, None, ["Alpha (fictional)", "Beta"]) == LocationTitle(
        surface_type="shutter", place="Alpha (fictional)"
    )


def test_criterion_48_with_neither_the_title_falls_back_to_the_id() -> None:
    assert location_title(location(), None, []) == LocationTitle()


def test_a_surface_type_must_be_in_the_vocabulary() -> None:
    assert _violation(location(surface_type="moon")) == "location.surface_type_unknown"


# Artwork.


def test_an_artwork_has_at_least_one_expression_type_from_the_vocabulary() -> None:
    assert _violation(artwork(1, expression_types=())) == "artwork.expression_types_required"
    assert _violation(artwork(1, expression_types=("fresco",))) == "artwork.expression_type_unknown"


def test_a_retired_expression_type_stays_on_a_record_but_is_not_newly_chosen() -> None:
    stored = artwork(1, expression_types=("sticker",))

    _check(replace(stored, title="Fictional title"), before=stored)
    assert _violation(stored) == "artwork.expression_type_unknown"
    assert (
        _violation(stored, before=artwork(1, expression_types=("mural",)))
        == "artwork.expression_type_unknown"
    )


def test_criterion_7_a_confirmed_attribution_without_citation_is_rejected() -> None:
    confirmed = Attribution(artist=5, certainty=Certainty.CONFIRMED)

    assert (
        _violation(artwork(1, attributions=(confirmed,)))
        == "attribution.confirmed_requires_citation"
    )
    _check(artwork(1, attributions=(replace(confirmed, citations=(9,)),)))
    _check(artwork(1, attributions=(replace(confirmed, certainty=Certainty.PROBABLE),)))


def test_an_artwork_has_one_attribution_per_artist() -> None:
    twice = (Attribution(5, Certainty.DISPUTED), Attribution(5, Certainty.PROBABLE))

    assert _violation(artwork(1, attributions=twice)) == "artwork.attributions_duplicated"


def test_blank_text_is_rejected() -> None:
    assert _violation(artwork(1, title="  ")) == "artwork.title_blank"


# Site, Area, Series (criterion 44).


def test_criterion_44_sites_areas_and_series_accept_an_optional_description() -> None:
    area = square(12.47, 41.88, 12.49, 41.90)
    for record in (
        Site("Fictional hall of fame"),
        Site("Fictional hall of fame", description="A fictional legal wall."),
        Area("Fictional rione", area),
        Area("Fictional rione", area, description="A fictional district."),
        Series("Fictional cats"),
        Series("Fictional cats", description="A fictional series of cats."),
    ):
        _check(record)


def test_an_area_is_a_polygon() -> None:
    assert _violation(Area("Fictional rione", point())) == "area.geometry_not_polygon"


def test_an_area_outside_the_instance_boundary_is_rejected() -> None:
    assert _violation(Area("Fictional rione", square(12.30, 41.88, 12.50, 41.90))) == (
        "area.outside_boundary"
    )


def test_a_name_is_required() -> None:
    assert _violation(Series("")) == "series.name_required"
    assert _violation(Artist(" ", ArtistKind.INDIVIDUAL)) == "artist.name_required"


# Source (criterion 45).


def test_criterion_45_a_source_without_a_title_is_rejected() -> None:
    assert _violation(Source(None)) == "source.title_required"  # type: ignore[arg-type]
    assert _violation(Source("   ")) == "source.title_required"
    _check(Source("Fictional article", author="Fictional author"))


def test_a_source_date_after_the_submission_is_rejected() -> None:
    future = UncertainDate(Precision.YEAR, Qualifier.EXACT, date(2030, 1, 1))

    with pytest.raises(ArchiveRuleViolation) as raised:
        _check(Source("Fictional article", date=future))

    assert raised.value.code == "uncertain_date.after_submission"


# Documentation item (criterion 49).


def test_criterion_49_an_image_without_alt_text_is_rejected() -> None:
    assert _violation(image(1, alt_text=None)) == "documentation_item.alt_text_required"


def test_criterion_49_an_alt_text_longer_than_250_characters_is_rejected() -> None:
    _check(image(1, alt_text="x" * 250))

    assert _violation(image(1, alt_text="x" * 251)) == "documentation_item.alt_text_too_long"


def test_uploaded_files_need_licence_credit_and_rights_basis() -> None:
    assert _violation(image(1, licence=None)) == "documentation_item.licence_required"
    assert _violation(image(1, licence="GPL-3.0")) == "documentation_item.licence_not_allowed"
    assert _violation(image(1, creator_credit=None)) == "documentation_item.creator_credit_required"
    assert (
        _violation(image(1, rights_basis=RightsBasis.THIRD_PARTY))
        == "documentation_item.origin_url_required"
    )
    _check(
        image(
            1,
            rights_basis=RightsBasis.THIRD_PARTY,
            origin_url="https://example.org/fictional.jpg",
        )
    )


def test_text_and_link_items_carry_their_content_and_no_file() -> None:
    _check(DocumentationItem(Medium.TEXT, OBSERVED, (1,), text="A fictional testimony."))
    _check(DocumentationItem(Medium.LINK, OBSERVED, (1,), url="https://example.org/a"))
    assert (
        _violation(DocumentationItem(Medium.LINK, OBSERVED, (1,)))
        == "documentation_item.url_required"
    )
    assert (
        _violation(
            DocumentationItem(Medium.LINK, OBSERVED, (1,), url="https://example.org/a", file="x")
        )
        == "documentation_item.file_not_applicable"
    )


def test_a_documentation_item_documents_at_least_one_artwork() -> None:
    assert _violation(image()) == "documentation_item.artworks_required"


def test_the_file_and_its_rights_never_change() -> None:
    stored = image(1)

    _check(replace(stored, alt_text="A corrected fictional alt text."), before=stored)
    assert (
        _violation(replace(stored, licence="CC0-1.0"), before=stored)
        == "documentation_item.licence_immutable"
    )
    assert (
        _violation(replace(stored, file="originals/other.jpg"), before=stored)
        == "documentation_item.file_immutable"
    )
