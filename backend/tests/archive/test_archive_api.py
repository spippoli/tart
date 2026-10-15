"""Archive records spec, Visibility and Public record pages, through the HTTP API:
criteria 16, 17, 18, 19, 20, 24, 27, 50, 54, 55, 56, 57, and 58 (the API's side).

The archive holds the fictional dataset (`tart.fictional`). Withdrawals, Merges, and
Redactions are set in the database, as the Rights and legal actions and Contribution
and moderation specs will set them; the read side is what these tests exercise.
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from archive_fixtures import Archive
from auth_fixtures import Api, open_api
from test_fictional_dataset import _seed

from tart.archive import SetField
from tart.fictional import Seeded

WITHDRAWN_AT = datetime(2026, 5, 4, 9, 0, tzinfo=UTC)


@pytest.fixture
def seeded(migrated_database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Seeded:
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    return _seed(migrated_database, tmp_path)


@pytest.fixture
def api(migrated_database: str, seeded: Seeded) -> Iterator[Api]:
    with open_api(migrated_database) as started:
        yield started


def _get(api: Api, path: str, **kwargs):
    return api.client.get(f"/api/archive/{path}", **kwargs)


def _withdraw(api: Api, record_id: int) -> None:
    api.query("UPDATE record SET withdrawn_at = $1 WHERE id = $2", WITHDRAWN_AT, record_id)


def _merge(api: Api, duplicate: int, survivor: int) -> None:
    api.query("UPDATE record SET merged_into = $1 WHERE id = $2", survivor, duplicate)


def _redact(api: Api, record_id: int, field: str) -> None:
    """Redact every operation of the record's Revisions that sets the field."""
    for revision in api.query("SELECT id, changes FROM revision WHERE record_id = $1", record_id):
        for index, change in enumerate(json.loads(revision["changes"])):
            if change.get("field") == field or change.get("collection") == field:
                api.query(
                    "INSERT INTO redaction (revision_id, operation, redacted_at) "
                    "VALUES ($1, $2, $3)",
                    revision["id"],
                    index,
                    WITHDRAWN_AT,
                )


def _as_moderator(api: Api) -> None:
    api.client.cookies.clear()
    number = api.sign_in("moderatrice@example.org")
    api.query("INSERT INTO user_role (user_id, role) VALUES ($1, 'moderator')", number)


def _as_user(api: Api) -> None:
    api.client.cookies.clear()
    api.sign_in("lettrice@example.org")


def _ids(entries: list[dict]) -> list[int]:
    return [entry["id"] for entry in entries]


# Criterion 16: each record kind at its route.


@pytest.mark.parametrize(
    ("segment", "key"),
    [
        ("artworks", "gatto"),
        ("artists", "nebbia"),
        ("locations", "cortile"),
        ("sites", "deposito"),
        ("areas", "quartiere"),
        ("series", "gatti"),
        ("sources", "fanzine"),
        ("documents", "foto-gatto"),
    ],
)
def test_criterion_16_each_kind_is_served_with_its_canonical_path(
    api: Api, seeded: Seeded, segment: str, key: str
) -> None:
    record_id = seeded.ids[key]

    response = _get(api, f"{segment}/{record_id}")

    assert response.status_code == 200, response.json()
    view = response.json()
    assert view["id"] == record_id
    slugged = segment in ("artworks", "artists", "sites", "areas", "series")
    assert view["path"].startswith(f"{record_id}-") if slugged else view["path"] == str(record_id)
    assert _get(api, f"{segment}/{record_id}/revisions").status_code == 200


def test_criterion_16_the_slug_comes_from_the_current_name(api: Api, seeded: Seeded) -> None:
    view = _get(api, f"artworks/{seeded.complete_artwork}").json()

    assert view["path"] == f"{seeded.complete_artwork}-il-gatto-che-legge"


def test_criterion_19_an_id_of_another_kind_or_unknown_is_404(api: Api, seeded: Seeded) -> None:
    for path in (f"artists/{seeded.complete_artwork}", "artworks/999999"):
        response = _get(api, path)
        assert response.status_code == 404
        assert response.json() == {"code": "record_not_found"}


# Criterion 50: an untitled Artwork is canonical at its bare id until it gets a title.


def test_criterion_50_an_untitled_artwork_gets_a_slug_with_its_title(
    api: Api, seeded: Seeded, migrated_database: str
) -> None:
    untitled = seeded.ids["senza-titolo"]
    assert _get(api, f"artworks/{untitled}").json()["path"] == str(untitled)

    Archive(migrated_database).write(SetField(untitled, "title", "Gatto in fuga"))

    assert _get(api, f"artworks/{untitled}").json()["path"] == f"{untitled}-gatto-in-fuga"


# Criterion 17: merged duplicates.


def test_criterion_17_a_merged_id_answers_301_to_the_survivor_without_chains(
    api: Api, seeded: Seeded
) -> None:
    first, second, survivor = seeded.ids["occhio"], seeded.ids["mani"], seeded.ids["onda"]
    _merge(api, first, second)  # an older Merge, then the survivor merged in turn
    _merge(api, second, survivor)

    response = _get(api, f"artworks/{first}", follow_redirects=False)

    assert response.status_code == 301
    assert response.headers["location"] == f"/api/archive/artworks/{survivor}"
    assert _get(api, f"artworks/{first}").json()["id"] == survivor


def test_criterion_17_a_merged_ids_revisions_answer_200_with_merged_into(
    api: Api, seeded: Seeded
) -> None:
    duplicate, survivor = seeded.ids["occhio"], seeded.ids["onda"]
    _merge(api, duplicate, survivor)

    response = _get(api, f"artworks/{duplicate}/revisions", follow_redirects=False)

    assert response.status_code == 200
    view = response.json()
    assert view["record"]["id"] == duplicate
    assert view["merged_into"]["id"] == survivor
    assert view["revisions"]


def test_a_merged_duplicate_leaves_the_lists(api: Api, seeded: Seeded) -> None:
    _merge(api, seeded.ids["coperto"], seeded.ids["gatto"])

    location = _get(api, f"locations/{seeded.ids['cortile']}").json()

    assert _ids(location["stratigraphy"]) == [seeded.complete_artwork]


# Criteria 18 and 58: withdrawn records.


@pytest.mark.parametrize("caller", ["anonymous", "user"])
def test_criteria_18_and_58_a_withdrawn_record_is_410_with_none_of_its_content(
    api: Api, seeded: Seeded, caller: str
) -> None:
    if caller == "user":
        _as_user(api)
    _withdraw(api, seeded.complete_artwork)

    for path in (
        f"artworks/{seeded.complete_artwork}",
        f"artworks/{seeded.complete_artwork}/revisions",
    ):
        response = _get(api, path)
        assert response.status_code == 410
        assert response.json() == {"code": "record_withdrawn"}
        assert "gatto" not in response.text.lower()


def test_criterion_18_a_withdrawn_documentation_item_is_410(api: Api, seeded: Seeded) -> None:
    item = seeded.ids["foto-gatto"]
    _withdraw(api, item)

    assert _get(api, f"documents/{item}").status_code == 410
    artwork = _get(api, f"artworks/{seeded.complete_artwork}").json()
    assert item not in _ids(artwork["gallery"])
    entries = artwork["timeline"]["dated"] + artwork["timeline"]["undated"]
    assert item not in [e["id"] for e in entries if e["entry"] == "item"]
    citations = [c["id"] for e in entries if e["entry"] == "event" for c in e["citations"]]
    assert item not in citations


# Criteria 20 and 27: no pending content and no sign of it.


@pytest.mark.parametrize("caller", ["anonymous", "user"])
def test_criteria_20_and_27_no_view_mentions_pending_submissions(
    api: Api, seeded: Seeded, caller: str
) -> None:
    if caller == "user":
        _as_user(api)

    for segment, key in (("artworks", "gatto"), ("locations", "cortile"), ("artists", "nebbia")):
        text = _get(api, f"{segment}/{seeded.ids[key]}").text.lower()
        assert "pending" not in text
        assert "submission" not in text


# Criterion 24: a withdrawn Artist.


def test_criterion_24_a_withdrawn_artists_attributions_and_memberships_are_absent(
    api: Api, seeded: Seeded
) -> None:
    lupo = seeded.ids["lupo"]
    _withdraw(api, lupo)

    disputed = _get(api, f"artworks/{seeded.ids['mani']}").json()["attribution"]
    assert lupo not in [a["artist"]["id"] for a in disputed["attributed"] + disputed["disputed"]]
    covered = _get(api, f"artworks/{seeded.ids['coperto']}").json()["attribution"]
    assert covered == {"attributed": [], "disputed": []}  # reads "Unknown artist"
    collective = _get(api, f"artists/{seeded.ids['collettivo']}").json()
    assert collective["members"] == []
    assert _get(api, f"artists/{lupo}").status_code == 410
    assert lupo not in _ids(_get(api, "artists").json()["items"])


# Criterion 54: a withdrawn Artwork.


def test_criterion_54_a_withdrawn_artwork_leaves_stratigraphy_series_and_covered_links(
    api: Api, seeded: Seeded
) -> None:
    _withdraw(api, seeded.complete_artwork)

    location = _get(api, f"locations/{seeded.ids['cortile']}").json()
    assert _ids(location["stratigraphy"]) == [seeded.ids["coperto"]]
    series = _get(api, f"series/{seeded.ids['gatti']}").json()
    assert seeded.complete_artwork not in _ids(series["artworks"])
    covered = _get(api, f"artworks/{seeded.ids['coperto']}").json()
    [event] = [e for e in covered["timeline"]["dated"] if e.get("type") == "covered"]
    assert event["covering"] is None  # reads "Covered", without a link
    assert seeded.complete_artwork not in _ids(covered["related"]["same_location"])


def test_criterion_54_a_location_with_no_public_artwork_lists_none(
    api: Api, seeded: Seeded
) -> None:
    for key in ("gatto", "coperto"):
        _withdraw(api, seeded.ids[key])

    location = _get(api, f"locations/{seeded.ids['cortile']}")

    assert location.status_code == 200
    assert location.json()["stratigraphy"] == []


# Criterion 55: withdrawn Series, Site, Area, and Source.


def test_criterion_55_withdrawn_series_site_and_source_leave_no_trace(
    api: Api, seeded: Seeded
) -> None:
    for key in ("gatti", "deposito", "fanzine"):
        _withdraw(api, seeded.ids[key])

    response = _get(api, f"artworks/{seeded.complete_artwork}")
    artwork = response.json()

    assert artwork["series"] == []
    assert artwork["where"]["site"] is None
    # The "where" line falls back to the next public value: the Areas.
    assert artwork["where"]["areas"]
    [attribution] = artwork["attribution"]["attributed"]
    assert attribution["citations"] == []
    assert attribution["certainty"] == "probable"  # confirmed without a public citation
    assert attribution["evidence_level"] == "reported"
    for name in ("Gatti di carta", "Ex deposito", "Muri che parlano"):
        assert name not in response.text


def test_criterion_55_a_withdrawn_area_leaves_the_where_line(api: Api, seeded: Seeded) -> None:
    _withdraw(api, seeded.ids["quartiere"])

    where = _get(api, f"artworks/{seeded.complete_artwork}").json()["where"]

    assert [area["name"] for area in where["areas"]] == ["Rione di Prova"]
    assert seeded.ids["quartiere"] not in _ids(_get(api, "areas").json()["items"])


# Criterion 56: a withdrawn Location.


def test_criterion_56_a_withdrawn_location_hides_the_position_only(
    api: Api, seeded: Seeded
) -> None:
    cortile = seeded.ids["cortile"]
    _withdraw(api, cortile)

    assert _get(api, f"locations/{cortile}").status_code == 410
    assert _get(api, f"locations/{cortile}/revisions").status_code == 410
    response = _get(api, f"artworks/{seeded.complete_artwork}")
    assert response.status_code == 200
    where = response.json()["where"]
    assert where == {
        "location": None,
        "location_withdrawn": True,
        "site": None,
        "areas": [],
        "nearby": [],
    }
    assert "12.495" not in response.text
    area = _get(api, f"areas/{seeded.ids['quartiere']}").json()
    assert seeded.complete_artwork not in _ids(area["artworks"])
    assert cortile not in _ids(area["locations"])
    site = _get(api, f"sites/{seeded.ids['deposito']}").json()
    assert site["artworks"] == [] and site["locations"] == []


# Criterion 57: the Moderator view.


def test_criterion_57_a_moderator_sees_a_withdrawn_record_with_its_date(
    api: Api, seeded: Seeded
) -> None:
    _withdraw(api, seeded.complete_artwork)
    _as_moderator(api)

    view = _get(api, f"artworks/{seeded.complete_artwork}").json()

    assert view["title"] == "Il gatto che legge"
    assert view["withdrawn_at"] == WITHDRAWN_AT.isoformat().replace("+00:00", "Z")
    revisions = _get(api, f"artworks/{seeded.complete_artwork}/revisions").json()
    assert revisions["withdrawn_at"] is not None
    # Withdrawn content stays out of lists for Moderators too.
    location = _get(api, f"locations/{seeded.ids['cortile']}").json()
    assert seeded.complete_artwork not in _ids(location["stratigraphy"])


def test_criterion_57_redacted_values_are_hidden_from_the_public_and_marked_for_moderators(
    api: Api, seeded: Seeded
) -> None:
    artwork = seeded.complete_artwork
    _redact(api, artwork, "description")

    public = _get(api, f"artworks/{artwork}")
    assert public.json()["description"] is None
    assert public.json()["redacted_fields"] == ["description"]
    assert "giornale" not in public.text
    changes = [
        change
        for revision in _get(api, f"artworks/{artwork}/revisions").json()["revisions"]
        for change in revision["changes"]
        if change.get("field") == "description"
    ]
    assert changes and all(c["redacted"] and c["new"] is None and c["old"] is None for c in changes)

    _as_moderator(api)
    moderator = _get(api, f"artworks/{artwork}").json()
    assert "giornale" in moderator["description"]
    assert moderator["redactions"][0]["field"] == "description"
    revisions = _get(api, f"artworks/{artwork}/revisions").json()["revisions"]
    marked = [c for r in revisions for c in r["changes"] if c.get("field") == "description"]
    assert all(c["redacted"] and c["redacted_at"] and c["new"] for c in marked)


def test_a_redacted_value_stays_hidden_as_a_later_previous_value(api: Api, seeded: Seeded) -> None:
    artwork = seeded.complete_artwork
    first = api.query(
        "SELECT id, changes FROM revision WHERE record_id = $1 ORDER BY id LIMIT 1", artwork
    )[0]
    [index] = [
        i
        for i, change in enumerate(json.loads(first["changes"]))
        if change.get("field") == "description"
    ]
    api.query(
        "INSERT INTO redaction (revision_id, operation, redacted_at) VALUES ($1, $2, $3)",
        first["id"],
        index,
        WITHDRAWN_AT,
    )

    view = _get(api, f"artworks/{artwork}").json()
    assert view["description"].endswith("firmato in basso.")  # the later value is current
    assert view["redacted_fields"] == []
    latest, *_ = _get(api, f"artworks/{artwork}/revisions").json()["revisions"]
    [change] = [c for c in latest["changes"] if c.get("field") == "description"]
    assert change["old"] is None and change["old_redacted"]
    assert change["new"].endswith("firmato in basso.")


# Revisions and indexes.


def test_revisions_name_the_submitter_never_the_moderator(api: Api, seeded: Seeded) -> None:
    view = _get(api, f"artworks/{seeded.complete_artwork}/revisions").json()

    assert [r["submitter"] for r in view["revisions"]] == ["Contributrice fittizia"] * 2
    assert "Moderatore" not in json.dumps(view)
    assert view["revisions"][0]["approved_at"] > view["revisions"][1]["approved_at"]
    assert str(seeded.ids["nebbia"]) in view["records"]


def test_the_timeline_links_each_event_to_its_revision(api: Api, seeded: Seeded) -> None:
    view = _get(api, f"artworks/{seeded.complete_artwork}").json()
    revisions = _get(api, f"artworks/{seeded.complete_artwork}/revisions").json()["revisions"]

    events = [e for e in view["timeline"]["dated"] if e["entry"] == "event"]
    assert {e["revision"] for e in events} == {r["id"] for r in revisions}
    assert all("submitter" not in e for e in events)


def test_an_index_lists_by_name_in_pages_of_24(api: Api, seeded: Seeded) -> None:
    page = _get(api, "artists").json()

    assert [item["name"] for item in page["items"]] == [
        "Collettivo Vernice Assente",
        "Lupo Inventato",
        "Nebbia Finta",
        "Ombra Supposta",
    ]
    assert (page["page"], page["page_size"], page["total"]) == (1, 24, 4)
    assert _get(api, "artists?page=2").json()["items"] == []
    assert _get(api, "artists?page=0").status_code == 422


# Criterion 22: the Timeline shows an image item's thumbnail and a text item's incipit.


def _timeline_items(artwork: dict) -> dict[int, dict]:
    entries = artwork["timeline"]["dated"] + artwork["timeline"]["undated"]
    return {e["id"]: e for e in entries if e["entry"] == "item"}


def test_criterion_22_an_image_item_on_the_timeline_carries_its_thumbnail(
    api: Api, seeded: Seeded
) -> None:
    artwork = _get(api, f"artworks/{seeded.complete_artwork}").json()
    item = _timeline_items(artwork)[seeded.ids["foto-gatto"]]

    assert item["medium"] == "image"
    assert item["file"] and "thumbnail" in item["renditions"]
    assert item["alt_text"].startswith("Immagine fittizia")
    assert item["incipit"] is None


def test_criterion_22_a_text_item_on_the_timeline_carries_its_incipit(
    api: Api, seeded: Seeded
) -> None:
    artwork = _get(api, f"artworks/{seeded.ids['scritta']}").json()
    items = _timeline_items(artwork)
    item = items[seeded.ids["testimonianza"]]

    assert item["medium"] == "text"
    assert item["incipit"] == "Testimonianza fittizia: la scritta era ancora leggibile."
    assert item["language"] == "it"
    assert item["file"] is None and item["alt_text"] is None


def test_criterion_22_a_link_item_on_the_timeline_carries_neither(api: Api, seeded: Seeded) -> None:
    artwork = _get(api, f"artworks/{seeded.ids['scritta']}").json()
    item = _timeline_items(artwork)[seeded.ids["collegamento"]]

    assert item["medium"] == "link"
    assert item["file"] is None and item["incipit"] is None
