"""Discovery spec, Ordering: acceptance criterion 29. Every record is fictional."""

# ruff: noqa: F401, F811
# The fixtures are imported for pytest and named again as parameters.
from datetime import UTC, datetime

from discovery_fixtures import Discovery, World, discovery, world, year

from tart.archive import Precision, Qualifier, UncertainDate


def test_ac29_the_default_order_is_most_recently_documented(
    world: World, discovery: Discovery
) -> None:
    old = world.artwork("Vecchio", documented=(year(2012),))
    new = world.artwork("Nuovo", documented=(year(2025),))
    middle = world.artwork("Medio", documented=(year(2018), year(2021)))

    assert discovery.ids() == [new, middle, old]


def test_ac29_first_documented_is_oldest_first_by_the_first_item(
    world: World, discovery: Discovery
) -> None:
    old = world.artwork("Vecchio", documented=(year(2012),))
    new = world.artwork("Nuovo", documented=(year(2025),))
    spanning = world.artwork("Esteso", documented=(year(2010), year(2024)))

    assert discovery.ids(order="oldest") == [spanning, old, new]


def test_ac29_unknown_and_missing_documentation_sort_last_in_both_directions(
    world: World, discovery: Discovery
) -> None:
    dated = world.artwork("Datato", documented=(year(2020),))
    unknown = world.artwork("Ignoto", documented=(UncertainDate.unknown(),))
    none = world.artwork("Nessuno", documented=())

    assert discovery.ids() == [dated, unknown, none]
    assert discovery.ids(order="oldest") == [dated, unknown, none]


def test_ac29_the_key_is_the_midpoint_ignoring_circa_and_ties_break_by_id(
    world: World, discovery: Discovery
) -> None:
    exact = world.artwork("Esatto", documented=(year(2016),))
    circa = world.artwork("Circa", documented=(year(2016, Qualifier.CIRCA),))
    later = world.artwork("Dopo", documented=(year(2017),))

    # c. 2016 has the key of 2016, though its range is wider; equal keys break by id.
    assert discovery.ids() == [later, exact, circa]
    assert discovery.ids(order="oldest") == [exact, circa, later]


def test_ac29_recently_added_is_by_the_approval_of_the_first_revision(
    world: World, discovery: Discovery
) -> None:
    first = world.artwork("Primo", approved=datetime(2026, 1, 1, tzinfo=UTC))
    third = world.artwork("Terzo", approved=datetime(2026, 9, 1, tzinfo=UTC))
    second = world.artwork("Secondo", approved=datetime(2026, 5, 1, tzinfo=UTC))

    assert discovery.ids(order="added") == [third, second, first]


def test_ac29_title_order_is_alphabetical_with_untitled_last(
    world: World, discovery: Discovery
) -> None:
    zebra = world.artwork("Zebra")
    untitled = world.artwork(None)
    accented = world.artwork("Èra")
    apple = world.artwork("Mela")
    alpha = world.artwork("Alba")

    assert discovery.ids(order="title") == [alpha, accented, apple, zebra, untitled]


def test_ac29_pages_are_stable_when_everything_ties(world: World, discovery: Discovery) -> None:
    made = [world.artwork(f"Pezzo {number}") for number in range(30)]

    pages = [discovery.ids(page=1), discovery.ids(page=2)]

    assert pages[0] + pages[1] == made
    assert len(pages[0]) == 24


def test_ac29_no_ordering_reads_an_engagement_signal(world: World, discovery: Discovery) -> None:
    first = world.artwork("Primo", documented=(year(2020),))
    second = world.artwork("Secondo", documented=(year(2019),))
    schema = discovery.api.client.get("/api/openapi.json").json()
    orders = schema["paths"]["/api/discovery/artworks"]["get"]["parameters"]

    for _ in range(5):  # looking at the second Artwork does not move it up
        discovery.api.client.get(f"/api/archive/artworks/{second}")

    assert discovery.ids() == [first, second]
    [order] = [p for p in orders if p["name"] == "order"]
    allowed = order["schema"]["anyOf"][0]["$ref"].rsplit("/", 1)[1]
    assert set(schema["components"]["schemas"][allowed]["enum"]) == {
        "recent",
        "oldest",
        "added",
        "title",
        "relevance",
    }
