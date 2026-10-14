"""Discovery spec, Filters: acceptance criteria 26, 27, and 28, and the filters they
combine. Every record is fictional.
"""

# ruff: noqa: F401, F811
# The fixtures are imported for pytest and named again as parameters.
import pytest
from discovery_fixtures import Discovery, World, discovery, world, year

from tart.archive import Certainty, Condition, Qualifier, UncertainDate


# Criterion 26: OR within a filter, AND across filters, no per-option counts.
def test_ac26_values_of_one_filter_are_alternatives(world: World, discovery: Discovery) -> None:
    intact = world.artwork("Intatto", condition=Condition.INTACT)
    covered = world.artwork("Coperto", condition=Condition.COVERED)
    destroyed = world.artwork("Distrutto", condition=Condition.DESTROYED)
    world.artwork("Sconosciuto", condition=Condition.UNKNOWN)

    assert set(discovery.ids(condition=["covered", "destroyed"])) == {covered, destroyed}
    assert discovery.ids(condition=["intact"]) == [intact]


def test_ac26_different_filters_all_apply(world: World, discovery: Discovery) -> None:
    both = world.artwork("Stencil distrutto", condition=Condition.DESTROYED)
    world.artwork("Stencil intatto", condition=Condition.INTACT)
    world.artwork("Murale distrutto", condition=Condition.DESTROYED, expression_types=("mural",))
    mural_or_stencil = ["mural", "stencil"]

    assert discovery.ids(condition=["destroyed"], type=["stencil"]) == [both]
    assert len(discovery.ids(condition=["destroyed"], type=mural_or_stencil)) == 2
    assert discovery.ids(condition=["destroyed"], type=["stencil"], q="intatto") == []


def test_ac26_all_nine_conditions_or_none_is_no_filter(world: World, discovery: Discovery) -> None:
    world.artwork("Uno", condition=Condition.INTACT)
    world.artwork("Due", condition=Condition.MISSING)
    nine = [condition.value for condition in Condition]

    assert len(discovery.ids(condition=nine)) == len(discovery.ids()) == 2


def test_ac26_the_response_has_a_total_and_no_per_option_counts(
    world: World,
    discovery: Discovery,
) -> None:
    world.artwork("Uno")

    page = discovery.artworks()

    assert page["total"] == 1
    assert set(page) == {"entries", "total", "page", "page_size", "also_matching", "left_out"}


def test_the_area_filter_is_membership_by_geometry_and_areas_may_overlap(
    world: World,
    discovery: Discovery,
) -> None:
    west = world.area("Ovest", 12.40, 41.85, 12.50, 41.95)
    east = world.area("Est", 12.45, 41.85, 12.56, 41.95)
    only_west = world.artwork("Solo ovest", at=world.place(12.42, 41.90))
    both = world.artwork("In entrambe", at=world.place(12.47, 41.90))
    only_east = world.artwork("Solo est", at=world.place(12.54, 41.90))

    assert discovery.ids(area=[west]) == [only_west, both]
    assert discovery.ids(area=[east]) == [both, only_east]
    assert set(discovery.ids(area=[west, east])) == {only_west, both, only_east}
    assert discovery.ids(area=[west], type=["mural"]) == []


def test_the_attribution_filter_reads_unknown_attributed_and_disputed(
    world: World,
    discovery: Discovery,
) -> None:
    artist, other = world.artist("Artista Uno"), world.artist("Artista Due")
    unknown = world.artwork("Ignoto")
    attributed = world.artwork("Attribuito", artists=(artist,))
    disputed = world.artwork("Contesto", artists=(artist, other), certainty=Certainty.DISPUTED)

    assert discovery.ids(attribution=["unknown"]) == [unknown]
    assert discovery.ids(attribution=["attributed"]) == [attributed]
    assert discovery.ids(attribution=["disputed"]) == [disputed]
    assert set(discovery.ids(attribution=["unknown", "disputed"])) == {unknown, disputed}


# Criterion 28: retired Expression types stay filterable; Artist and Series come by link.
def test_ac28_a_retired_expression_type_remains_filterable(
    world: World,
    discovery: Discovery,
) -> None:
    sticker = world.artwork("Adesivo", expression_types=("mural",))
    world.artwork("Stencil")
    # The vocabulary retired `sticker` after the Artwork used it.
    world.query("UPDATE artwork SET expression_types = ARRAY['sticker'] WHERE id = $1", sticker)

    assert discovery.ids(type=["sticker"]) == [sticker]


def test_ac28_artist_and_series_filter_by_id(world: World, discovery: Discovery) -> None:
    artist, series = world.artist("Artista"), world.series("Serie")
    signed = world.artwork("Firmato", artists=(artist,))
    listed = world.artwork("In serie", series=(series,))
    world.artwork("Altro")

    assert discovery.ids(artist=artist) == [signed]
    assert discovery.ids(series=series) == [listed]
    assert discovery.ids(artist=artist, series=series) == []


def test_a_withdrawn_artist_or_series_filters_nothing_in(
    world: World, discovery: Discovery
) -> None:
    artist = world.artist("Artista")
    signed = world.artwork("Firmato", artists=(artist,))
    assert discovery.ids(artist=artist) == [signed]

    world.withdraw(artist)

    assert discovery.ids(artist=artist) == []


# Criterion 27: date filters match by overlap of ranges; Created between counts what it leaves out.
def test_ac27_created_between_matches_by_overlap_of_the_stored_range(
    world: World,
    discovery: Discovery,
) -> None:
    around_2016 = world.artwork("Circa 2016", created=year(2016, Qualifier.CIRCA))
    before_2012 = world.artwork("Prima del 2012", created=year(2012, Qualifier.BEFORE))
    in_2020 = world.artwork("Nel 2020", created=year(2020))

    # c. 2016 is 2015-2017: it matches "from 2017" but not "from 2018".
    assert discovery.ids(created_from=2017) == [around_2016, in_2020]
    assert discovery.ids(created_from=2018) == [in_2020]
    # before 2012 reaches back from the end of 2011, with an open start.
    assert discovery.ids(created_to=2012) == [before_2012]
    assert discovery.ids(created_from=1990, created_to=1991) == [before_2012]
    assert discovery.ids(created_to=2014) == [before_2012]
    assert discovery.ids(created_from=2015, created_to=2016) == [around_2016]


def test_ac27_artworks_without_a_creation_date_are_left_out_and_counted(
    world: World,
    discovery: Discovery,
) -> None:
    dated = world.artwork("Datato", created=year(2020))
    world.artwork("Senza creazione")
    world.artwork("Creazione ignota", created=UncertainDate.unknown())

    page = discovery.artworks(created_from=2019)

    assert [entry["id"] for entry in page["entries"]] == [dated]
    assert page["left_out"] == 2
    assert discovery.artworks()["left_out"] == 0


def test_ac27_the_left_out_count_follows_the_other_filters(
    world: World, discovery: Discovery
) -> None:
    world.artwork("Con data", created=year(2020), condition=Condition.INTACT)
    world.artwork("Senza uno", condition=Condition.INTACT)
    world.artwork("Senza due", condition=Condition.DESTROYED)

    assert discovery.artworks(created_from=2019, condition=["intact"])["left_out"] == 1
    assert discovery.artworks(created_from=2019, q="senza")["left_out"] == 2


def test_ac27_documented_between_matches_any_observed_date_of_a_public_item(
    world: World,
    discovery: Discovery,
) -> None:
    twice = world.artwork("Due fotografie", documented=(year(2010), year(2020)))
    once = world.artwork("Una fotografia", documented=(year(2015),))
    approx = world.artwork("Circa", documented=(year(2016, Qualifier.CIRCA),))

    assert discovery.ids(documented_from=2019) == [twice]
    assert discovery.ids(documented_to=2012) == [twice]
    assert discovery.ids(documented_from=2011, documented_to=2014) == []
    assert discovery.ids(documented_from=2017, documented_to=2017) == [approx]
    assert set(discovery.ids(documented_from=2015, documented_to=2015)) == {once, approx}


def test_ac27_an_artwork_with_no_dated_public_item_never_matches_documented_between(
    world: World,
    discovery: Discovery,
) -> None:
    world.artwork("Data ignota", documented=(UncertainDate.unknown(),))
    dated = world.artwork("Datata", documented=(year(2020),))

    assert discovery.ids(documented_from=1, documented_to=9999) == [dated]


def test_the_viewport_restricts_to_the_locations_whose_sign_is_inside(
    world: World,
    discovery: Discovery,
) -> None:
    inside = world.artwork("Dentro", at=world.place(12.48, 41.90))
    world.artwork("Fuori", at=world.place(12.55, 41.93))

    assert discovery.ids(bbox="12.47,41.89,12.49,41.91") == [inside]
    assert len(discovery.ids()) == 2


def test_a_list_entry_names_the_artists_whose_attribution_is_only_probable(
    world: World,
    discovery: Discovery,
) -> None:
    artist = world.artist("Artista Uno")
    world.artwork("Probabile", artists=(artist,), certainty=Certainty.PROBABLE)

    entry = discovery.artworks()["entries"][0]

    assert entry["probable"] == [artist]
    assert [link["id"] for link in entry["attributed"]] == [artist]


# Criterion 51: a bad value, such as a reversed range, is ignored without an error.
def test_ac51_a_reversed_year_range_is_ignored(world: World, discovery: Discovery) -> None:
    world.artwork("Nel 2016", created=year(2016))
    world.artwork("Nel 2020", created=year(2020))

    assert len(discovery.ids(created_from=2020, created_to=2016)) == 2
    assert len(discovery.ids(documented_from=2020, documented_to=2016)) == 2


# Validation: a malformed or absurd value is a 422, never a 500.
@pytest.mark.parametrize(
    "params",
    [
        {"bbox": "nan,41,13,42"},
        {"bbox": "12,41,inf,42"},
        {"bbox": "12,41,13"},
        {"bbox": "-181,41,13,42"},
        {"bbox": "12,-91,13,42"},
        {"bbox": "12,41,13,91"},
        {"bbox": "13,41,12,42"},
        {"bbox": "12,42,13,41"},
        {"page": 10**30},
        {"page": 0},
        {"area": 10**30},
        {"area": [1] * 51},
        {"artist": 10**30},
        {"series": 10**30},
        {"type": ["mural"] * 51},
        {"condition": ["intact"] * 51},
    ],
)
def test_a_value_out_of_range_is_a_422(discovery: Discovery, params: dict) -> None:
    paths = ["/api/discovery/artworks"]
    if not {"bbox", "page"} & params.keys():  # the Locations answer takes neither
        paths.append("/api/discovery/locations")
    for path in paths:
        assert discovery.api.client.get(path, params=params).status_code == 422


def test_a_location_id_out_of_range_is_a_422(discovery: Discovery) -> None:
    assert discovery.api.client.get(f"/api/discovery/locations/{10**30}").status_code == 422
