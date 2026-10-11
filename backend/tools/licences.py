"""Dependency licence allow-list for the Python dependencies (ADR 0011 §8).

    uv run python tools/licences.py

Permissive licences are allowed for any dependency. Weak-copyleft licences are
allowed only for unmodified, dynamically linked libraries, which a person has to
judge, so such a dependency must be listed in `licences.toml` with its licence and
the reason. Strong copyleft is never allowed as a dependency: it may only run as a
separate program in its own container. The test suite runs this check, so CI
fails on a dependency outside the tiers.
"""

import re
import sys
import tomllib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib.metadata import distributions
from pathlib import Path

PERMISSIVE = frozenset(
    {
        "MIT",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "Apache-2.0",
        "ISC",
        "PSF-2.0",
        "Python-2.0",
        "Zlib",
        "BlueOak-1.0.0",
    }
)
WEAK_COPYLEFT = frozenset(
    {
        "LGPL-2.1-only",
        "LGPL-2.1-or-later",
        "LGPL-3.0-only",
        "LGPL-3.0-or-later",
        "MPL-2.0",
    }
)
STRONG_COPYLEFT_PREFIXES = ("GPL-", "AGPL-")

# Trove classifiers, used only when a package declares no SPDX expression.
CLASSIFIERS = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: Apache Software License": "Apache-2.0",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    "License :: OSI Approved :: zlib/libpng License": "Zlib",
}

# Free-text `License` fields that name one licence, for packages with no SPDX
# expression and no classifier to fall back on.
LICENCE_NAMES = {
    "Apache License 2.0": "Apache-2.0",
}

POLICY = Path(__file__).parents[1] / "licences.toml"
PROJECT = "tart"

_SPDX_ID = re.compile(r"[A-Za-z0-9.+-]+")
_TOKEN = re.compile(r"\(|\)|[A-Za-z0-9.+-]+")


@dataclass(frozen=True)
class Dependency:
    name: str
    version: str
    licence: str | None

    @classmethod
    def from_metadata(
        cls,
        name: str,
        version: str,
        expression: str | None,
        licence_field: str | None,
        classifiers: Iterable[str],
    ) -> Dependency:
        licence = expression
        if licence is None and licence_field:
            text = licence_field.strip()
            licence = text if _is_expression(text) else LICENCE_NAMES.get(text)
        if licence is None:
            ids = sorted({CLASSIFIERS[c] for c in classifiers if c in CLASSIFIERS})
            licence = " AND ".join(ids) or None
        return cls(name=name, version=version, licence=licence)


@dataclass(frozen=True)
class Reviewed:
    licence: str
    tier: str
    reason: str = ""


def _is_expression(text: str) -> bool:
    tokens = text.replace("(", " ( ").replace(")", " ) ").split()
    if not all(
        token in ("(", ")", "AND", "OR", "WITH") or _SPDX_ID.fullmatch(token) for token in tokens
    ):
        return False
    # Free text such as "Apache 2.0" is made of id-like words but does not parse.
    try:
        satisfies(text, lambda _: True)
    except ValueError, IndexError:
        return False
    return True


def satisfies(expression: str, allowed: Callable[[str], bool]) -> bool:
    """Evaluates an SPDX expression: OR takes any alternative, AND needs every part.

    `X WITH exception` counts as `X`, since an SPDX exception only adds permissions.
    """
    tokens = _TOKEN.findall(expression)
    position = 0

    def peek() -> str | None:
        return tokens[position] if position < len(tokens) else None

    def take() -> str:
        nonlocal position
        position += 1
        return tokens[position - 1]

    def any_of() -> bool:
        result = all_of()
        while peek() == "OR":
            take()
            result = all_of() or result
        return result

    def all_of() -> bool:
        result = term()
        while peek() == "AND":
            take()
            result = term() and result
        return result

    def term() -> bool:
        if peek() == "(":
            take()
            result = any_of()
            take()  # ")"
            return result
        licence = take()
        if peek() == "WITH":
            take()
            take()
        return allowed(licence)

    result = any_of()
    if peek() is not None:
        raise ValueError(f"invalid SPDX expression: {expression}")
    return result


def _is_strong_copyleft(licence: str) -> bool:
    return licence.startswith(STRONG_COPYLEFT_PREFIXES)


TIERS: dict[str, Callable[[str], bool]] = {
    "weak-copyleft": lambda licence: licence in PERMISSIVE | WEAK_COPYLEFT,
    # A licence not named in ADR 0011 that a person has judged permissive.
    "permissive": lambda licence: not _is_strong_copyleft(licence) and licence not in WEAK_COPYLEFT,
}


def violations(dependencies: Iterable[Dependency], reviewed: dict[str, Reviewed]) -> list[str]:
    found = []
    for dependency in dependencies:
        label = f"{dependency.name} {dependency.version}"
        if dependency.licence is None:
            found.append(f"{label}: no licence found")
            continue
        if satisfies(dependency.licence, PERMISSIVE.__contains__):
            continue
        review = reviewed.get(dependency.name)
        if review is None or review.licence != dependency.licence:
            found.append(f"{label}: {dependency.licence} is outside the licence tiers")
        elif review.tier not in TIERS or not satisfies(review.licence, TIERS[review.tier]):
            found.append(
                f"{label}: the review of {review.licence} as {review.tier} does not fit that tier"
            )
    return found


def installed_dependencies() -> list[Dependency]:
    dependencies = []
    for distribution in distributions():
        metadata = distribution.metadata
        if metadata["Name"] == PROJECT:
            continue
        dependencies.append(
            Dependency.from_metadata(
                name=metadata["Name"],
                version=metadata["Version"],
                expression=metadata.get("License-Expression"),
                licence_field=metadata.get("License"),
                classifiers=metadata.get_all("Classifier") or [],
            )
        )
    return sorted(dependencies, key=lambda d: d.name.lower())


def load_reviewed(path: Path = POLICY) -> dict[str, Reviewed]:
    policy = tomllib.loads(path.read_text(encoding="utf-8"))
    return {name: Reviewed(**entry) for name, entry in policy.get("reviewed", {}).items()}


if __name__ == "__main__":
    found = violations(installed_dependencies(), load_reviewed())
    print("\n".join(found) or "Every dependency is within the licence tiers.")
    sys.exit(1 if found else 0)
