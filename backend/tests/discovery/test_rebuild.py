"""`tart discovery rebuild` brings the Discovery index of an existing archive up to date.
Every record is fictional."""

# ruff: noqa: F401, F811
# The fixtures are imported for pytest and named again as parameters.
import pytest
from discovery_fixtures import Discovery, World, discovery, world

from tart.cli import main as run_cli


def test_rebuild_fills_the_index_of_an_archive_that_predates_it(
    world: World, discovery: Discovery, capsys: pytest.CaptureFixture[str]
) -> None:
    first = world.artwork("Gatto sul muro")
    second = world.artwork("Cane sul muro")
    for table in ("discovery_name", "discovery_documented", "discovery_artwork"):
        world.query(f"DELETE FROM {table}")
    assert discovery.ids(q="gatto") == []

    assert run_cli(["discovery", "rebuild"]) == 0

    assert "rebuilt: 2 Artworks" in capsys.readouterr().out
    assert discovery.ids(q="gatto") == [first]
    assert set(discovery.ids()) == {first, second}
