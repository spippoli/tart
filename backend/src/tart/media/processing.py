"""Turn an uploaded file into a sanitised original and its renditions, or refuse it
(Foundations spec, 3. Storage and media pipeline, Processing).

Pure and synchronous: bytes in, bytes out. The worker runs it in a thread.
"""

import io
import struct
from dataclasses import dataclass
from datetime import datetime

import pi_heif
import pypdfium2
from PIL import ExifTags, Image, ImageOps

from tart.media import (
    FILE_TYPE_UNSUPPORTED,
    FILE_UNREADABLE,
    IMAGE_TOO_LARGE,
    MAX_PIXELS,
    Format,
    Rendition,
    rendition_edge,
)
from tart.media.detect import detect
from tart.media.sanitise import SanitiseError, sanitise

pi_heif.register_heif_opener()
# Pillow's own guard warns past this and refuses past twice this; the pipeline refuses
# anything past it, before decoding.
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

_PILLOW_FORMATS = {
    Format.JPEG: "JPEG",
    Format.PNG: "PNG",
    Format.WEBP: "WEBP",
    Format.AVIF: "AVIF",
    Format.HEIC: "HEIF",
}
WEBP_QUALITY = 82
# Errors of a file that does not decode: Pillow, pi-heif, and PDFium raise these.
_DECODE_ERRORS = (OSError, ValueError, SyntaxError, EOFError, struct.error, SanitiseError)


@dataclass(frozen=True)
class Suggestions:
    """What EXIF suggests to the Submission form; never stored as a Location (ADR 0012)."""

    observed_date: str | None = None
    """The capture date, `YYYY-MM-DD`."""
    point: tuple[float, float] | None = None
    """Where the camera was, `(longitude, latitude)`."""


@dataclass(frozen=True)
class Processed:
    format: Format
    original: bytes
    """The file to store as the original: without GPS or device identifiers."""
    renditions: dict[Rendition, tuple[bytes, int, int]]
    """Each rendition's WebP bytes, width, and height."""
    suggestions: Suggestions


@dataclass(frozen=True)
class Rejected:
    code: str


def process(data: bytes, cap: int) -> Processed | Rejected:
    """Validate, sanitise, and derive renditions capped at `cap` pixels on the long edge."""
    file_format = detect(data[:64])
    if file_format is None:
        return Rejected(FILE_TYPE_UNSUPPORTED)
    try:
        if file_format is Format.PDF:
            return _pdf(data, cap)
        return _image(data, file_format, cap)
    except Image.DecompressionBombError:
        return Rejected(IMAGE_TOO_LARGE)
    except _DECODE_ERRORS:
        return Rejected(FILE_UNREADABLE)


def _image(data: bytes, file_format: Format, cap: int) -> Processed | Rejected:
    with Image.open(io.BytesIO(data), formats=[_PILLOW_FORMATS[file_format]]) as image:
        width, height = image.size
        if width * height > MAX_PIXELS:
            return Rejected(IMAGE_TOO_LARGE)
        image.seek(0)  # an animated image keeps only its first frame
        image.load()
        animated = getattr(image, "n_frames", 1) > 1
        suggestions = _suggestions(image.getexif())
        icc = image.info.get("icc_profile") if image.mode in ("RGB", "RGBA") else None
        upright = _flatten(ImageOps.exif_transpose(image))
    if animated:
        # The first frame alone becomes the original, losslessly, with no metadata.
        buffer = io.BytesIO()
        upright.save(buffer, "WEBP", lossless=True, icc_profile=icc)
        original, file_format = buffer.getvalue(), Format.WEBP
    else:
        original = sanitise(data, file_format)
    return Processed(file_format, original, _renditions(upright, cap, icc), suggestions)


def _pdf(data: bytes, cap: int) -> Processed | Rejected:
    try:
        document = pypdfium2.PdfDocument(data)
    except pypdfium2.PdfiumError:
        return Rejected(FILE_UNREADABLE)
    try:
        if len(document) == 0:
            return Rejected(FILE_UNREADABLE)
        page = document[0]
        width, height = page.get_size()
        if width <= 0 or height <= 0:
            return Rejected(FILE_UNREADABLE)
        # The preview's long edge is the cap: every rendition derives from it.
        scale = cap / max(width, height)
        if (width * scale) * (height * scale) > MAX_PIXELS:
            return Rejected(IMAGE_TOO_LARGE)
        preview = _flatten(page.render(scale=scale).to_pil())
    except pypdfium2.PdfiumError:
        return Rejected(FILE_UNREADABLE)
    finally:
        document.close()
    return Processed(Format.PDF, data, _renditions(preview, cap, None), Suggestions())


def _flatten(image: Image.Image) -> Image.Image:
    """RGB, or RGBA when the image has transparency: what WebP stores."""
    transparent = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
    return image.convert("RGBA" if transparent else "RGB")


def _renditions(
    image: Image.Image, cap: int, icc: bytes | None
) -> dict[Rendition, tuple[bytes, int, int]]:
    long_edge = max(image.size)
    renditions = {}
    for rendition in Rendition:
        edge = rendition_edge(rendition, cap, long_edge)
        resized = image.copy()
        resized.thumbnail((edge, edge), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        # Only what is passed here is written: no EXIF, XMP, or IPTC.
        resized.save(buffer, "WEBP", quality=WEBP_QUALITY, method=4, icc_profile=icc)
        renditions[rendition] = (buffer.getvalue(), *resized.size)
    return renditions


def _suggestions(exif: Image.Exif) -> Suggestions:
    return Suggestions(observed_date=_capture_date(exif), point=_position(exif))


def _capture_date(exif: Image.Exif) -> str | None:
    value = exif.get_ifd(ExifTags.IFD.Exif).get(ExifTags.Base.DateTimeOriginal)
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip("\x00 "), "%Y:%m:%d %H:%M:%S").date().isoformat()
    except ValueError:
        return None


def _position(exif: Image.Exif) -> tuple[float, float] | None:
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    try:
        latitude = _degrees(gps[ExifTags.GPS.GPSLatitude], gps[ExifTags.GPS.GPSLatitudeRef], "S")
        longitude = _degrees(gps[ExifTags.GPS.GPSLongitude], gps[ExifTags.GPS.GPSLongitudeRef], "W")
    except KeyError, TypeError, ValueError, ZeroDivisionError:
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or latitude == longitude == 0:
        return None
    return round(longitude, 6), round(latitude, 6)


def _degrees(value: tuple[float, float, float], reference: str, negative: str) -> float:
    degrees, minutes, seconds = (float(part) for part in value)
    sign = -1 if reference.strip("\x00 ").upper() == negative else 1
    return sign * (degrees + minutes / 60 + seconds / 3600)
