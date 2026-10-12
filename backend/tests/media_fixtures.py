"""The media pipeline's fixture files (Foundations spec, Testing Decisions): built here
with Pillow and PDFium, except the HEIC, which needs an encoder TART does not ship.

Every position is fictional: Piazza Navona's coordinates, not a real photographer's.
"""

import io
import struct
import zlib
from functools import cache
from pathlib import Path

from PIL import ExifTags, Image

FIXTURES = Path(__file__).parent / "fixtures" / "media"
HEIC_WITH_GPS = FIXTURES / "gps.heic"
"""320 by 240, with GPS, make, model, a body serial number, a capture date
(2024-11-20), and an XMP serial number. Made once with pillow-heif, outside TART."""

LONGITUDE, LATITUDE = 12.4823, 41.8955
CAPTURE_DATE = "2025-05-03"
SERIAL = "SN-FICTIONAL-0042"
XMP = (
    b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
    b'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description '
    b'xmlns:exif="http://ns.adobe.com/exif/1.0/" exif:GPSLatitude="41,53.73N" '
    b'xmlns:aux="http://ns.adobe.com/exif/1.0/aux/" aux:SerialNumber="SN-FICTIONAL-0042"/>'
    b"</rdf:RDF></x:xmpmeta>"
)


def exif(orientation: int = 1) -> Image.Exif:
    """EXIF with a position, a capture date, and device identifiers."""
    data = Image.Exif()
    data[ExifTags.Base.Make] = "FictionalCam"
    data[ExifTags.Base.Model] = "Model F"
    data[ExifTags.Base.Orientation] = orientation
    details = data.get_ifd(ExifTags.IFD.Exif)
    details[ExifTags.Base.DateTimeOriginal] = "2025:05:03 10:15:00"
    details[ExifTags.Base.BodySerialNumber] = SERIAL
    gps = data.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitudeRef] = "N"
    gps[ExifTags.GPS.GPSLatitude] = (41.0, 53.0, 43.8)
    gps[ExifTags.GPS.GPSLongitudeRef] = "E"
    gps[ExifTags.GPS.GPSLongitude] = (12.0, 28.0, 56.28)
    return data


def picture(width: int, height: int, mode: str = "RGB") -> Image.Image:
    """Two colours, the left half red, so orientation shows in the pixels."""
    image = Image.new(mode, (width, height), "navy")
    image.paste("red", (0, 0, width // 2, height))
    return image


def encode(image: Image.Image, file_format: str, **options: object) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, file_format, **options)
    return buffer.getvalue()


def jpeg_with_gps(width: int = 400, height: int = 300, orientation: int = 1) -> bytes:
    return encode(picture(width, height), "JPEG", exif=exif(orientation), xmp=XMP)


def png_with_gps() -> bytes:
    return encode(picture(400, 300), "PNG", exif=exif(), pnginfo=_png_text())


def _png_text():
    from PIL.PngImagePlugin import PngInfo

    info = PngInfo()
    info.add_itxt("XML:com.adobe.xmp", XMP.decode())
    info.add_text("Comment", SERIAL)
    return info


def webp_with_gps() -> bytes:
    return encode(picture(400, 300), "WEBP", exif=exif(), xmp=XMP)


def avif_with_gps() -> bytes:
    return encode(picture(400, 300), "AVIF", exif=exif(), xmp=XMP)


def animated_webp() -> bytes:
    """Two frames: the first red, the second blue."""
    first, second = Image.new("RGB", (200, 100), "red"), Image.new("RGB", (200, 100), "blue")
    return encode(first, "WEBP", save_all=True, append_images=[second], duration=100)


def pdf() -> bytes:
    """One A4 page, as Pillow writes it: about 595 by 842 points."""
    return encode(picture(1240, 1754), "PDF", resolution=150)


def png_header_only(width: int, height: int) -> bytes:
    """A PNG that declares its size and holds one tiny, unfinished image data chunk."""
    return _png(width, height, zlib.compress(b"\x00" * 64))


@cache
def decompression_bomb() -> bytes:
    """About 400 kB that inflate to a 20 000 by 20 000 greyscale image of 400 MB."""
    width = height = 20_000
    compressor = zlib.compressobj(9)
    row = b"\x00" * (width + 1)  # a filter byte, then the row
    rows = row * 500
    data = b"".join(compressor.compress(rows) for _ in range(height // 500))
    return _png(width, height, data + compressor.flush(), colour_type=0)


def _png(width: int, height: int, idat: bytes, colour_type: int = 2) -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = struct.pack(">I", zlib.crc32(kind + body))
        return struct.pack(">I", len(body)) + kind + body + crc

    header = struct.pack(">IIBBBBB", width, height, 8, colour_type, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    )
