# /// script
# requires-python = ">=3.14"
# dependencies = ["fonttools==4.60.1"]
# ///
"""Rebuild fonts/SortsMillGoudy-SmallCaps.ttf: `uv run small_caps.py`.

MapLibre draws a font file's default glyphs and applies no OpenType feature, so the
small caps of Sorts Mill Goudy (its `smcp` feature) are reached by a font of their
own: a copy of the Regular whose character map sends each lowercase letter to its
small-cap glyph, renamed "Sorts Mill Goudy Small Caps". Capitals stay full size. The
result is a Modified Version under the SIL Open Font License 1.1, like its source
(no Reserved Font Name).
"""

from pathlib import Path

from fontTools.ttLib import TTFont

FONTS = Path(__file__).parent / "fonts"
SOURCE = FONTS / "SortsMillGoudy-Regular.ttf"
TARGET = FONTS / "SortsMillGoudy-SmallCaps.ttf"
FAMILY = "Sorts Mill Goudy Small Caps"
POSTSCRIPT_NAME = "SortsMillGoudy-SmallCaps"


def small_caps(font: TTFont) -> dict[str, str]:
    """Each glyph the `smcp` feature replaces, with its small-cap glyph."""
    table = font["GSUB"].table
    lookups = {
        index
        for record in table.FeatureList.FeatureRecord
        if record.FeatureTag == "smcp"
        for index in record.Feature.LookupListIndex
    }
    mapping: dict[str, str] = {}
    for index in sorted(lookups):
        lookup = table.LookupList.Lookup[index]
        for subtable in lookup.SubTable:
            if lookup.LookupType == 7:  # extension: the real subtable is inside
                subtable = subtable.ExtSubTable
            mapping.update(getattr(subtable, "mapping", {}))
    return mapping


def main() -> None:
    font = TTFont(SOURCE, recalcTimestamp=False)  # the same file on every run
    mapping = small_caps(font)
    replaced = 0
    for table in font["cmap"].tables:
        for code, glyph in list(table.cmap.items()):
            if chr(code).islower() and glyph in mapping:
                table.cmap[code] = mapping[glyph]
                replaced += 1
    # OpenType name IDs: 1 family, 4 full name, 6 PostScript name, 16 typographic family.
    names = {1: FAMILY, 4: FAMILY, 6: POSTSCRIPT_NAME, 16: FAMILY}
    for record in list(font["name"].names):
        if record.nameID in names:
            font["name"].setName(
                names[record.nameID],
                record.nameID,
                record.platformID,
                record.platEncID,
                record.langID,
            )
    font.save(TARGET)
    print(f"{TARGET.name} written: {replaced} character map entries sent to small caps")


if __name__ == "__main__":
    main()
