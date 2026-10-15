"""The incipit of a text Documentation item (criterion 22)."""

from tart.archive_read.reader import INCIPIT_LENGTH, incipit


def test_a_short_text_is_its_own_incipit_without_an_ellipsis() -> None:
    assert incipit("La scritta era ancora leggibile.") == "La scritta era ancora leggibile."


def test_whitespace_is_collapsed() -> None:
    assert incipit("Prima riga\n\n  seconda\tparola") == "Prima riga seconda parola"


def test_a_long_text_is_cut_at_a_word_boundary_with_an_ellipsis() -> None:
    text = " ".join(["parola"] * 60)
    result = incipit(text)

    assert result is not None and result.endswith("…")
    assert len(result) <= INCIPIT_LENGTH + 1
    assert set(result.removesuffix("…").split()) == {"parola"}


def test_a_text_of_exactly_the_limit_is_not_cut() -> None:
    text = "a" * INCIPIT_LENGTH

    assert incipit(text) == text


def test_one_unbroken_word_longer_than_the_limit_is_cut_at_the_limit() -> None:
    assert incipit("x" * 500) == "x" * INCIPIT_LENGTH + "…"


def test_an_empty_text_has_no_incipit() -> None:
    assert incipit(None) is None
    assert incipit("   ") is None
