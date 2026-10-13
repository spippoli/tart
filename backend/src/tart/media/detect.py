"""The type of a file from its first bytes, never from its name or declared type."""

from tart.media import Format

# ISO base media file brands (ISO/IEC 23008-12, AV1 Image File Format).
_AVIF_BRANDS = {b"avif", b"avis"}
_HEIC_BRANDS = {b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx"}
_HEIF_BRANDS = {b"mif1", b"msf1"}
"""Generic HEIF brands: the image inside is HEVC unless an AVIF brand says otherwise."""


def detect(head: bytes) -> Format | None:
    """The accepted type that the file's first bytes announce, or None."""
    if head.startswith(b"\xff\xd8\xff"):
        return Format.JPEG
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return Format.PNG
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return Format.WEBP
    if head.startswith(b"%PDF-"):
        return Format.PDF
    if head[4:8] == b"ftyp":
        brands = _brands(head)
        if brands & _AVIF_BRANDS:
            return Format.AVIF
        if brands & (_HEIC_BRANDS | _HEIF_BRANDS):
            return Format.HEIC
    return None


def _brands(head: bytes) -> set[bytes]:
    """The major brand and the compatible brands of an `ftyp` box."""
    size = min(int.from_bytes(head[:4]), len(head))
    brands = {head[8:12]}
    brands.update(head[offset : offset + 4] for offset in range(16, size - 3, 4))
    return brands
