"""Discovery spec, The map (Data) and Selection and the side panel: the Locations response
and the panel endpoint. Every record is fictional."""

# ruff: noqa: F401, F811
# The fixtures are imported for pytest and named again as parameters.
from archive_fixtures import location, point, square
from discovery_fixtures import Discovery, World, discovery, world, year

from tart.archive import Condition, Create, Geometry, GeometryKind, New


def _features(discovery: Discovery, **params) -> dict[int, dict]:
    return {f["properties"]["id"]: f for f in discovery.locations(**params)["features"]}


def test_one_feature_per_location_with_a_matching_artwork(
    world: World, discovery: Discovery
) -> None:
    shared = world.place()
    world.artwork("Uno", at=shared)
    world.artwork("Due", at=shared, condition=Condition.DESTROYED)
    alone = world.artwork("Tre", condition=Condition.UNKNOWN)
    [only] = world.query("SELECT location_id FROM artwork WHERE id = $1", alone)

    features = _features(discovery)

    assert len(features) == 2
    assert features[shared]["properties"] | {} == {
        "id": shared,
        "present": 1,
        "unknown": 0,
        "disappeared": 1,
        "group": "present",
        "count": 2,
        "point": [12.4823, 41.8955],
        "approximate": False,
        "radius": None,
    }
    assert features[only["location_id"]]["properties"]["group"] == "unknown"


def test_filters_apply_to_artworks_and_a_location_shows_only_what_matches(
    world: World, discovery: Discovery
) -> None:
    shared = world.place()
    world.artwork("Presente", at=shared)
    world.artwork("Sparito", at=shared, condition=Condition.REMOVED)
    gone = world.artwork("Tutto sparito", condition=Condition.DESTROYED)
    [gone_at] = world.query("SELECT location_id FROM artwork WHERE id = $1", gone)

    only_present = _features(discovery, condition=["intact"])
    only_gone = _features(discovery, condition=["destroyed", "removed"])

    assert list(only_present) == [shared]
    assert only_present[shared]["properties"]["count"] == 1
    assert set(only_gone) == {shared, gone_at["location_id"]}
    assert only_gone[shared]["properties"]["group"] == "disappeared"
    assert _features(discovery, q="nessuna corrispondenza") == {}


def test_the_prevailing_group_is_present_then_unknown_then_disappeared(
    world: World, discovery: Discovery
) -> None:
    mixed = world.place()
    world.artwork("A", at=mixed, condition=Condition.UNKNOWN)
    world.artwork("B", at=mixed, condition=Condition.COVERED)
    assert _features(discovery)[mixed]["properties"]["group"] == "unknown"

    world.artwork("C", at=mixed, condition=Condition.DAMAGED)
    assert _features(discovery)[mixed]["properties"]["group"] == "present"
    assert (
        _features(discovery, condition=["covered"])[mixed]["properties"]["group"] == "disappeared"
    )


def test_lines_and_polygons_keep_their_geometry_and_a_point_on_it(
    world: World, discovery: Discovery
) -> None:
    line = Geometry(GeometryKind.LINE, ((12.47, 41.89), (12.49, 41.89)))
    ring = square(12.50, 41.90, 12.52, 41.92)
    line_id = world.archive.ids(world.archive.write(Create(New("l"), location(geometry=line))))[0]
    ring_id = world.archive.ids(world.archive.write(Create(New("l"), location(geometry=ring))))[0]
    world.artwork("Sulla linea", at=line_id)
    world.artwork("Nell'area", at=ring_id)

    features = _features(discovery)

    assert features[line_id]["geometry"]["type"] == "LineString"
    assert features[line_id]["properties"]["point"] == [12.48, 41.89]  # half way along
    assert features[ring_id]["geometry"]["type"] == "Polygon"
    [lon, lat] = features[ring_id]["properties"]["point"]
    assert 12.50 < lon < 12.52 and 41.90 < lat < 41.92


def test_coordinates_are_rounded_to_six_decimals_and_approximation_is_carried(
    world: World, discovery: Discovery
) -> None:
    place = world.place(12.48234567891, 41.89554321987, approximate=True, uncertainty_radius=40)
    world.artwork("Approssimata", at=place)

    properties = _features(discovery)[place]["properties"]

    assert properties["point"] == [12.482346, 41.895543]
    assert (properties["approximate"], properties["radius"]) == (True, 40)


def test_sites_are_labelled_at_the_centroid_of_their_matching_locations_and_areas_by_name(
    world: World, discovery: Discovery
) -> None:
    site = world.site("Mercato Esempio")
    world.area("Quartiere Prova", 12.50, 41.90, 12.52, 41.92)
    world.artwork("Uno", at=world.place(12.40, 41.90, site=site))
    world.artwork("Due", at=world.place(12.42, 41.92, site=site), condition=Condition.DESTROYED)

    everything = discovery.locations()
    intact = discovery.locations(condition=["intact"])

    [label] = everything["sites"]
    assert label["name"] == "Mercato Esempio"
    assert label["path"] == f"{site}-mercato-esempio"
    assert label["point"] == [12.41, 41.91]
    assert intact["sites"][0]["point"] == [12.4, 41.9]
    assert everything["areas"] == [
        {"name": "Quartiere Prova", "point": everything["areas"][0]["point"]}
    ]
    assert discovery.locations(q="nessuna corrispondenza")["sites"] == []


# The ETag: a repeat costs a 304.
def test_the_response_is_revalidated_with_an_etag_and_a_repeat_is_304(
    world: World, discovery: Discovery
) -> None:
    world.artwork("Uno")
    client = discovery.api.client

    first = client.get("/api/discovery/locations")
    repeat = client.get(
        "/api/discovery/locations", headers={"If-None-Match": first.headers["ETag"]}
    )

    assert first.headers["Cache-Control"] == "no-cache"
    assert repeat.status_code == 304 and repeat.content == b""
    assert repeat.headers["ETag"] == first.headers["ETag"]


def test_the_etag_follows_the_normalised_query_and_the_archive_changes(
    world: World, discovery: Discovery
) -> None:
    world.artwork("Gatto")
    client = discovery.api.client

    def tag(**params) -> str:
        return client.get("/api/discovery/locations", params=params).headers["ETag"]

    plain = tag()
    assert tag(q="  gatto ") == tag(q="gatto") != plain
    assert tag(q="g") == plain  # under 2 characters counts as absent
    assert tag(condition=["destroyed"]) != plain
    assert tag(order="relevance") == plain  # no `q`: relevance is ignored

    world.artwork("Un altro")
    assert tag() != plain


def test_a_stale_etag_gets_the_full_response(world: World, discovery: Discovery) -> None:
    world.artwork("Uno")
    client = discovery.api.client
    stale = client.get("/api/discovery/locations").headers["ETag"]
    world.artwork("Due")

    response = client.get("/api/discovery/locations", headers={"If-None-Match": stale})

    assert response.status_code == 200
    assert len(response.json()["features"]) == 2


# The Location panel.
def test_the_panel_has_the_header_and_the_stratigraphy_of_matching_artworks(
    world: World, discovery: Discovery
) -> None:
    site = world.site("Mercato Esempio")
    place = world.place(site=site)
    old = world.artwork("Strato vecchio", at=place, created=year(2010))
    new = world.artwork("Strato nuovo", at=place, created=year(2022))
    gone = world.artwork(
        "Strato sparito", at=place, condition=Condition.REMOVED, created=year(2016)
    )
    client = discovery.api.client

    panel = client.get(f"/api/discovery/locations/{place}", params={"condition": ["intact"]}).json()

    assert panel["location"]["id"] == place
    assert panel["site"]["name"] == "Mercato Esempio"
    assert [entry["id"] for entry in panel["entries"]] == [new, old]  # most recent first
    assert (panel["matches"], panel["other"]) == (True, 1)
    everything = client.get(f"/api/discovery/locations/{place}").json()
    assert [entry["id"] for entry in everything["entries"]] == [new, gone, old]
    assert everything["other"] == 0


def test_a_location_with_no_matching_artwork_shows_its_full_stratigraphy_flagged(
    world: World, discovery: Discovery
) -> None:
    place = world.place()
    kept = world.artwork("Uno", at=place)
    other = world.artwork("Due", at=place)

    panel = discovery.api.client.get(
        f"/api/discovery/locations/{place}", params={"condition": ["destroyed"]}
    ).json()

    assert {entry["id"] for entry in panel["entries"]} == {kept, other}
    assert (panel["matches"], panel["other"]) == (False, 0)


def test_a_public_location_without_public_artworks_opens_empty(
    world: World, discovery: Discovery
) -> None:
    place = world.place()

    panel = discovery.api.client.get(f"/api/discovery/locations/{place}").json()

    assert (panel["entries"], panel["matches"]) == ([], False)


def test_a_withdrawn_merged_or_missing_location_answers_the_same_404(
    world: World, discovery: Discovery
) -> None:
    withdrawn, merged, kept = world.place(), world.place(), world.place()
    world.withdraw(withdrawn)
    world.merge(merged, kept)
    client = discovery.api.client

    answers = [client.get(f"/api/discovery/locations/{id_}") for id_ in (withdrawn, merged, 99999)]

    assert {(r.status_code, r.text) for r in answers} == {
        (404, '{"code":"location_not_available"}')
    }


def test_the_panel_entries_carry_what_a_list_entry_shows(
    world: World, discovery: Discovery
) -> None:
    artist = world.artist("Artista Fittizio")
    site = world.site("Mercato Esempio")
    place = world.place(site=site)
    artwork = world.artwork("Con tutto", at=place, artists=(artist,), documented=(year(2020),))

    [entry] = discovery.artworks()["entries"]

    assert entry["id"] == artwork and entry["location"] == place
    assert entry["site"]["name"] == "Mercato Esempio"
    assert entry["attributed"][0]["name"] == "Artista Fittizio" and entry["disputed"] == []
    assert entry["condition"]["group"] == "present"
    assert entry["last_documented"]["first"] == "2020-01-01"
    assert entry["thumbnail"] is not None and entry["latest_item_medium"] == "image"


def test_an_entry_says_where_its_locations_sign_sits_for_show_on_map(
    world: World, discovery: Discovery
) -> None:
    place = world.place()
    world.artwork("Qui", at=place)

    [entry] = discovery.artworks()["entries"]

    assert entry["location"] == place
    assert entry["location_point"] == [12.4823, 41.8955]
