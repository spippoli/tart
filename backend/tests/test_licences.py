import pytest
from licences import Dependency, Reviewed, installed_dependencies, load_reviewed, violations


def _dep(licence: str | None, name: str = "pkg") -> Dependency:
    return Dependency(name=name, version="1.0", licence=licence)


def test_every_installed_dependency_is_within_the_licence_tiers() -> None:
    found = violations(installed_dependencies(), load_reviewed())

    assert found == [], "\n".join(found)


@pytest.mark.parametrize(
    "licence",
    [
        "MIT",
        "BSD-3-Clause",
        "Apache-2.0",
        "ISC",
        "PSF-2.0",
        "Zlib",
        "Apache-2.0 OR BSD-2-Clause",
        "(MIT AND Zlib)",
        "Apache-2.0 WITH LLVM-exception",
        "GPL-3.0-only OR MIT",
    ],
)
def test_a_permissive_licence_is_allowed_for_any_dependency(licence: str) -> None:
    assert violations([_dep(licence)], {}) == []


@pytest.mark.parametrize(
    "licence",
    ["GPL-3.0-only", "AGPL-3.0-or-later", "MIT AND GPL-2.0-or-later", "LGPL-3.0-only", "MPL-2.0"],
)
def test_a_copyleft_licence_not_reviewed_is_refused(licence: str) -> None:
    assert violations([_dep(licence)], {}) == [f"pkg 1.0: {licence} is outside the licence tiers"]


def test_an_unknown_licence_is_refused() -> None:
    assert violations([_dep(None)], {}) == ["pkg 1.0: no licence found"]


def test_a_reviewed_weak_copyleft_dependency_is_allowed() -> None:
    reviewed = {"pkg": Reviewed(licence="LGPL-3.0-only", tier="weak-copyleft")}

    assert violations([_dep("LGPL-3.0-only")], reviewed) == []


def test_a_review_no_longer_matching_the_licence_is_refused() -> None:
    reviewed = {"pkg": Reviewed(licence="LGPL-3.0-only", tier="weak-copyleft")}

    assert violations([_dep("GPL-3.0-only")], reviewed) == [
        "pkg 1.0: GPL-3.0-only is outside the licence tiers"
    ]


def test_strong_copyleft_cannot_be_reviewed_in() -> None:
    reviewed = {"pkg": Reviewed(licence="GPL-3.0-only", tier="weak-copyleft")}

    assert violations([_dep("GPL-3.0-only")], reviewed) == [
        "pkg 1.0: the review of GPL-3.0-only as weak-copyleft does not fit that tier"
    ]


def test_classifiers_stand_in_for_a_missing_licence_expression() -> None:
    dependency = Dependency.from_metadata(
        name="pkg",
        version="1.0",
        expression=None,
        licence_field=None,
        classifiers=["License :: OSI Approved :: MIT License"],
    )

    assert dependency.licence == "MIT"


@pytest.mark.parametrize(
    ("licence_field", "classifiers", "expected"),
    [
        # Free text whose words happen to look like SPDX ids is not an expression.
        ("Apache 2.0", ["License :: OSI Approved :: Apache Software License"], "Apache-2.0"),
        ("Dual License", ["License :: OSI Approved :: Apache Software License"], "Apache-2.0"),
        # A well-known licence name with no classifier to fall back on.
        ("Apache License 2.0", [], "Apache-2.0"),
        ("Apache-2.0", [], "Apache-2.0"),
    ],
)
def test_a_free_text_licence_field_is_read_as_its_licence(
    licence_field: str, classifiers: list[str], expected: str
) -> None:
    dependency = Dependency.from_metadata(
        name="pkg",
        version="1.0",
        expression=None,
        licence_field=licence_field,
        classifiers=classifiers,
    )

    assert dependency.licence == expected
