"""Slug derivation and the id-slug path segment of record URLs (ADR 0010, archive-records spec)."""

import pytest

from tart.archive import record_path_segment, slugify


def test_criterion_51_the_slug_strips_accents_and_joins_alphanumeric_runs() -> None:
    assert slugify("Lupa à rebours — Stencil n°3") == "lupa-a-rebours-stencil-n-3"


@pytest.mark.parametrize("name", ["", "   ", "— · —", "★★★", "東京"])
def test_criterion_51_a_name_with_no_alphanumeric_character_gives_the_bare_id(name: str) -> None:
    assert slugify(name) == ""
    assert record_path_segment(4821, name) == "4821"


def test_criterion_51_a_named_record_is_at_id_dash_slug() -> None:
    assert record_path_segment(4821, "Lupa à rebours — Stencil n°3") == (
        "4821-lupa-a-rebours-stencil-n-3"
    )


def test_an_untitled_record_is_at_the_bare_id() -> None:
    assert record_path_segment(4821, None) == "4821"


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("  Via dei Volsci!  ", "via-dei-volsci"),
        ("Straße Øresund Œuvre Łódź", "strasse-oresund-oeuvre-lodz"),
        ("CAPITALI E Minuscole", "capitali-e-minuscole"),
        ("Muro n. 12 / bis", "muro-n-12-bis"),
    ],
)
def test_the_slug_is_lowercase_ascii_with_single_dashes(name: str, slug: str) -> None:
    assert slugify(name) == slug


def test_a_long_slug_is_cut_at_60_characters_on_the_last_dash_that_fits() -> None:
    name = "Ritratto collettivo del quartiere di San Lorenzo dopo la grande nevicata"

    slug = slugify(name)

    assert slug == "ritratto-collettivo-del-quartiere-di-san-lorenzo-dopo-la"
    assert len(slug) <= 60


def test_a_slug_of_exactly_60_characters_is_kept_whole() -> None:
    name = "a" * 30 + " " + "b" * 29

    assert slugify(name) == "a" * 30 + "-" + "b" * 29


def test_a_slug_ending_right_before_a_dash_at_60_is_kept_up_to_it() -> None:
    name = "a" * 60 + " tail"

    assert slugify(name) == "a" * 60


def test_a_single_word_longer_than_60_characters_is_cut_at_60() -> None:
    assert slugify("x" * 75) == "x" * 60
