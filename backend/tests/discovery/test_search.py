"""Discovery spec, Search: acceptance criteria 22, 23, 24, 25, 53, 54, and 55.

Every record is fictional.
"""

# ruff: noqa: F401, F811
# The fixtures are imported for pytest and named again as parameters.
from discovery_fixtures import Discovery, World, discovery, world, year

from tart.archive import Create, New
from tart.archive import Source as SourceRecord
from tart.discovery.filters import MAX_QUERY_LENGTH, Filters, Order, normalise_query


# Criterion 22: only public, approved content is found.
def test_ac22_a_withdrawn_artwork_or_location_and_a_merged_duplicate_are_not_found(
    world: World,
    discovery: Discovery,
) -> None:
    kept = world.artwork("Gatto in vista")
    withdrawn = world.artwork("Gatto ritirato")
    duplicate = world.artwork("Gatto doppio")
    on_withdrawn_location = world.artwork("Gatto su muro ritirato")
    world.withdraw(withdrawn)
    world.merge(duplicate, kept)
    location = world.query("SELECT location_id FROM artwork WHERE id = $1", on_withdrawn_location)
    world.withdraw(location[0]["location_id"])

    assert discovery.ids(q="gatto") == [kept]
    assert discovery.ids() == [kept]
    assert [f["properties"]["count"] for f in discovery.locations()["features"]] == [1]


def test_ac22_what_a_withdrawn_artist_or_a_redaction_hides_is_not_searchable(
    world: World,
    discovery: Discovery,
) -> None:
    artist = world.artist("Ottavia Fittizia", "La Civetta")
    signed = world.artwork("Civetta sul tetto", artists=(artist,))
    redacted = world.artwork("Titolo cancellato")
    assert discovery.ids(q="ottavia") == [signed]
    assert [k["kind"] for k in discovery.artworks(q="ottavia")["also_matching"]["kinds"]] == [
        "artist"
    ]

    world.withdraw(artist)
    world.redact(redacted, "title")
    world.settle(artist, redacted)

    assert discovery.ids(q="ottavia") == []
    assert discovery.ids(q="civetta") == [signed]  # its own title still matches
    assert discovery.artworks(q="ottavia")["also_matching"] is None
    assert discovery.ids(q="cancellato") == []
    assert [
        entry["title"] for entry in discovery.artworks()["entries"] if entry["id"] == redacted
    ] == [None]


# Criterion 23: where `q` matches, tolerating accents and typos.
def test_ac23_q_matches_title_description_artist_series_site_and_area_names(
    world: World,
    discovery: Discovery,
) -> None:
    artist = world.artist("Mira Fittizia", "La Lince")
    series = world.series("Serie dei Tetti")
    site = world.site("Mercato Esempio")
    world.area("Quartiere Prova", 12.50, 41.90, 12.52, 41.92)
    in_site = world.place(site=site)
    in_area = world.place(12.51, 41.91)

    by_title = world.artwork("Gatto sul muro")
    by_description = world.artwork(None, description="Il murale raffigura grandi gatti colorati")
    by_artist = world.artwork("Senza titolo noto", artists=(artist,))
    by_series = world.artwork("Pezzo uno", series=(series,))
    by_site = world.artwork("Pezzo due", at=in_site)
    by_area = world.artwork("Pezzo tre", at=in_area)

    assert discovery.ids(q="gatto") == [by_title, by_description]
    assert discovery.ids(q="mira") == [by_artist]
    assert discovery.ids(q="lince") == [by_artist]  # an Alias
    assert discovery.ids(q="tetti") == [by_series]
    assert discovery.ids(q="mercato") == [by_site]
    assert discovery.ids(q="quartiere") == [by_area]


def test_ac23_q_tolerates_accents_and_typos(world: World, discovery: Discovery) -> None:
    city = world.artwork("Città del sole")
    garden = world.artwork("Giardino segreto")

    assert discovery.ids(q="citta") == [city]
    assert discovery.ids(q="CITTÀ") == [city]
    assert discovery.ids(q="giardno") == [garden]  # a missing letter
    assert discovery.ids(q="giard") == [garden]  # a prefix


def test_ac23_descriptions_are_matched_with_italian_stemming(
    world: World,
    discovery: Discovery,
) -> None:
    painted = world.artwork(None, description="Un gatto dipinto in grigio")

    assert discovery.ids(q="gatti") == [painted]
    assert discovery.ids(q="dipinti") == [painted]


def test_ac23_sources_documentation_and_event_notes_are_not_searched(
    world: World,
    discovery: Discovery,
) -> None:
    from discovery_fixtures import event, image, location  # local: builders only this test needs

    from tart.archive import Artwork

    changeset = [
        Create(New("src"), SourceRecord(title="Rilievo misterioso")),
        Create(New("loc"), location()),
        Create(
            New("art"),
            Artwork(
                location=New("loc"),
                expression_types=("stencil",),
                title="Opera ordinaria",
                history_events=(event(note="nota misteriosa"),),
                sources=(New("src"),),
            ),
        ),
        Create(New("doc"), image(New("art"), alt_text="didascalia misteriosa")),
    ]
    world.archive.write(*changeset)

    assert discovery.ids(q="misteriosa") == []
    assert discovery.ids(q="misterioso") == []
    assert len(discovery.ids(q="ordinaria")) == 1


# Criterion 24: the UI language never affects search.
def test_ac24_the_same_q_returns_the_same_results_in_every_ui_language(
    world: World,
    discovery: Discovery,
) -> None:
    world.artwork("Muro dipinto")
    world.artwork(None, description="Un muro bianco")

    results = {
        language: discovery.api.client.get(
            "/api/discovery/artworks", params={"q": "muro"}, headers={"Accept-Language": language}
        ).json()
        for language in ("it", "en", "de")
    }

    assert len(results["it"]["entries"]) == 2
    assert results["it"] == results["en"] == results["de"]


# Criterion 25 and 55: "Also matching".
def test_ac25_also_matching_links_artists_series_sites_and_areas_by_name_or_alias(
    world: World,
    discovery: Discovery,
) -> None:
    world.artist("Luna Fittizia")
    world.artist("Sole Fittizio", "Luna Nera")
    world.series("Serie Luna")
    world.site("Piazza Luna")
    world.area("Luna Park", 12.50, 41.90, 12.52, 41.92)
    world.artist("Marte Fittizio")

    kinds = discovery.artworks(q="luna")["also_matching"]["kinds"]

    assert [kind["kind"] for kind in kinds] == ["artist", "series", "site", "area"]
    artists = kinds[0]["items"]
    assert [item["record"]["name"] for item in artists] == ["Luna Fittizia", "Sole Fittizio"]
    assert [item["alias"] for item in artists] == [None, "Luna Nera"]


def test_ac55_also_matching_shows_three_per_kind_and_counts_the_rest(
    world: World,
    discovery: Discovery,
) -> None:
    for name in ("Rosa Verde", "Rosa", "Rosa Blu", "Rosa Gialla", "Rosario Lontano", "Marte"):
        world.site(name)

    [kind] = discovery.artworks(q="rosa")["also_matching"]["kinds"]

    # Similarity descending, then name; a prefix ("Rosario") matches, "Marte" does not.
    assert [item["record"]["name"] for item in kind["items"]] == ["Rosa", "Rosa Blu", "Rosa Gialla"]
    assert kind["total"] == 5


def test_ac55_also_matching_is_absent_without_a_query_or_a_match(
    world: World,
    discovery: Discovery,
) -> None:
    world.site("Piazza Fittizia")
    world.artwork("Un pezzo")

    assert discovery.artworks()["also_matching"] is None
    assert discovery.artworks(q="inesistente")["also_matching"] is None
    assert discovery.artworks(q="x")["also_matching"] is None  # under 2 characters
    assert discovery.artworks(q="piazza")["also_matching"] is not None


def test_ac55_also_matching_is_the_same_on_every_page(world: World, discovery: Discovery) -> None:
    world.site("Piazza del Gatto")
    for number in range(30):
        world.artwork(f"Gatto numero {number}")

    first, second = discovery.artworks(q="gatto"), discovery.artworks(q="gatto", page=2)

    assert first["total"] == second["total"] == 30
    assert len(first["entries"]) == 24 and len(second["entries"]) == 6
    assert first["also_matching"] == second["also_matching"] is not None


# Criterion 53: normalisation, thresholds, and ranking.
def test_ac53_q_is_trimmed_collapsed_ignored_when_short_and_truncated() -> None:
    assert normalise_query("  gatto \t sul   muro ") == "gatto sul muro"
    assert normalise_query(None) is None
    assert normalise_query("   ") is None
    assert normalise_query("g") is None
    assert normalise_query(" g ") is None
    assert normalise_query("gi") == "gi"
    long = normalise_query("parola " * 40)
    assert long is not None and len(long) <= MAX_QUERY_LENGTH
    assert long == ("parola " * 40)[:MAX_QUERY_LENGTH].strip()


def test_ac53_a_short_q_is_absent_and_whitespace_is_collapsed(
    world: World,
    discovery: Discovery,
) -> None:
    cat = world.artwork("Gatto sul muro")
    dog = world.artwork("Cane")

    assert set(discovery.ids(q="g")) == {cat, dog}
    assert discovery.ids(q="  gatto \t  sul   muro ") == [cat]


def test_ac53_a_name_matches_at_a_similarity_of_half_or_more(
    world: World,
    discovery: Discovery,
) -> None:
    near = world.artwork("Giardino")
    world.artwork("Zebra")

    assert discovery.ids(q="giardino") == [near]
    assert discovery.ids(q="giardnio") == [near]
    assert discovery.ids(q="qwerty") == []


def test_ac53_a_matching_title_ranks_above_a_mention_in_a_description(
    world: World,
    discovery: Discovery,
) -> None:
    mention = world.artwork(None, description="Dietro il gatto dorme un gatto, il gatto sogna")
    titled = world.artwork("Gatto")

    assert discovery.ids(q="gatto") == [titled, mention]


def test_ac53_a_title_outranks_an_artist_a_series_and_a_site(
    world: World,
    discovery: Discovery,
) -> None:
    artist = world.artist("Gatto Fittizio")
    series = world.series("Gatto Serie")
    site = world.site("Gatto Mercato")
    by_site = world.artwork("Uno", at=world.place(site=site))
    by_series = world.artwork("Due", series=(series,))
    by_artist = world.artwork("Tre", artists=(artist,))
    by_title = world.artwork("Gatto")

    assert discovery.ids(q="gatto") == [by_title, by_artist, by_series, by_site]


# Criterion 54: relevance ties and the offer of relevance.
def test_ac54_relevance_ties_break_by_most_recently_documented_then_id(
    world: World,
    discovery: Discovery,
) -> None:
    older = world.artwork("Gatto", documented=(year(2019),))
    newer = world.artwork("Gatto", documented=(year(2024),))
    same_year = world.artwork("Gatto", documented=(year(2024),))
    undated_only = world.artwork("Gatto", documented=())

    assert discovery.ids(q="gatto") == [newer, same_year, older, undated_only]


def test_ac54_relevance_is_offered_only_with_q(world: World, discovery: Discovery) -> None:
    older = world.artwork("Zebra", documented=(year(2019),))
    newer = world.artwork("Gatto", documented=(year(2024),))

    assert discovery.ids(order="relevance") == [newer, older]
    assert discovery.ids(order="relevance") == discovery.ids()
    assert Filters(order=Order.RELEVANCE).effective_order is Order.RECENT
    assert Filters(q="gatto").effective_order is Order.RELEVANCE
    assert Filters(q="gatto", order=Order.TITLE).effective_order is Order.TITLE
    assert discovery.ids(q="gatto", order="title") == [newer]
