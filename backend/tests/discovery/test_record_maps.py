"""Discovery spec, Mini-map and Index name filter: acceptance criteria 36 and 66, the
API's side. Every record is fictional.
"""

# ruff: noqa: F401, F811
# The fixtures are imported for pytest and named again as parameters.
from discovery_fixtures import Discovery, World, discovery, world

from tart.archive import Condition


def _get(discovery: Discovery, path: str, **params: object) -> dict:
    response = discovery.api.client.get(f"/api/archive/{path}", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _names(page: dict) -> list[str | None]:
    return [item["name"] for item in page["items"]]


# Criterion 36: the name filter matches as Search does, alphabetical, 24 per page.
def test_ac36_an_index_filters_by_name_ignoring_accents_and_typos(
    world: World, discovery: Discovery
) -> None:
    world.series("Gatti di quartiere")
    world.series("Città vuota")
    world.series("Cani randagi")

    assert _names(_get(discovery, "series", name="citta")) == ["Città vuota"]
    assert _names(_get(discovery, "series", name="gatti")) == ["Gatti di quartiere"]
    assert _get(discovery, "series", name="zzzz")["items"] == []
    assert len(_get(discovery, "series", name=" ")["items"]) == 3


def test_ac36_the_artists_index_also_matches_aliases(world: World, discovery: Discovery) -> None:
    world.artist("Lupo Inventato", "Il Lupetto")
    world.artist("Nebbia Finta")

    assert _names(_get(discovery, "artists", name="lupetto")) == ["Lupo Inventato"]
    assert _names(_get(discovery, "artists", name="nebbia")) == ["Nebbia Finta"]


def test_ac36_the_filtered_index_is_alphabetical_and_paged_by_24(
    world: World, discovery: Discovery
) -> None:
    for number in range(30):
        world.site(f"Muro Finto {number:02d}")
    world.site("Altro luogo")

    first = _get(discovery, "sites", name="muro finto")
    second = _get(discovery, "sites", name="muro finto", page=2)

    assert (first["total"], first["page_size"], len(first["items"])) == (30, 24, 24)
    assert len(second["items"]) == 6
    assert _names(first)[0] == "Muro Finto 00"
    assert _names(second)[-1] == "Muro Finto 29"


def test_ac36_a_redacted_name_is_not_found(world: World, discovery: Discovery) -> None:
    hidden = world.series("Serie nascosta")
    world.series("Serie visibile")
    world.redact(hidden, "name")

    assert _names(_get(discovery, "series", name="nascosta")) == []


# Criterion 66: the record's response carries the public Locations within 500 m.
def test_ac66_the_record_carries_the_locations_within_500_metres(
    world: World, discovery: Discovery
) -> None:
    here = world.place(12.4823, 41.8955)
    near = world.place(12.4823, 41.8995)  # about 440 m north
    world.place(12.4823, 41.9015)  # about 660 m north
    artwork = world.artwork("Qui", at=here)

    location = _get(discovery, f"locations/{here}")
    artwork_view = _get(discovery, f"artworks/{artwork}")

    assert [place["id"] for place in location["nearby"]] == [near]
    assert location["nearby"][0]["point"] == [12.4823, 41.8995]
    assert artwork_view["where"]["nearby"] == location["nearby"]
    assert location["point"] == [12.4823, 41.8955]
    assert artwork_view["where"]["location"]["point"] == [12.4823, 41.8955]


def test_ac66_a_withdrawn_location_is_not_nearby(world: World, discovery: Discovery) -> None:
    here = world.place()
    gone = world.place(12.4823, 41.8975)
    kept = world.place(12.4833, 41.8955)
    world.withdraw(gone)

    assert [place["id"] for place in _get(discovery, f"locations/{here}")["nearby"]] == [kept]


# Criterion 65: a Series' map has only the Locations of its public Artworks.
def test_ac65_a_series_page_lists_only_its_artworks_locations_with_their_conditions(
    world: World, discovery: Discovery
) -> None:
    series = world.series("Serie fittizia")
    intact = world.artwork("Uno", series=(series,), condition=Condition.INTACT)
    destroyed = world.artwork("Due", series=(series,), condition=Condition.DESTROYED)
    world.artwork("Fuori serie")

    page = _get(discovery, f"series/{series}")
    where = {
        id_: _get(discovery, f"artworks/{id_}")["where"]["location"]["id"]
        for id_ in (intact, destroyed)
    }

    counts = {place["id"]: (place["present"], place["disappeared"]) for place in page["locations"]}
    assert counts == {where[intact]: (1, 0), where[destroyed]: (0, 1)}


def test_ac65_a_series_without_a_visible_location_lists_none(
    world: World, discovery: Discovery
) -> None:
    series = world.series("Serie vuota")
    artwork = world.artwork("Ritirata", series=(series,))
    world.withdraw(artwork)

    assert _get(discovery, f"series/{series}")["locations"] == []
