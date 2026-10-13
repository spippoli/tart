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
from PIL import ExifTags, Image

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
    # Memory: a 100-megapixel bitmap is 400 MB, so the full-size image is decoded once and
    # never copied; everything after the first downscale works on the large rendition.
    with Image.open(io.BytesIO(data), formats=[_PILLOW_FORMATS[file_format]]) as image:
        size = image.size
        if size[0] * size[1] > MAX_PIXELS:
            return Rejected(IMAGE_TOO_LARGE)
        image.seek(0)  # an animated image keeps only its first frame
        large = _fit(size, rendition_edge(Rendition.LARGE, cap, max(size)))
        if file_format is Format.JPEG:
            # Decodes the whole file at 1/2, 1/4, or 1/8 scale, never below `large`.
            image.draft(None, large)
        image.load()
        animated = getattr(image, "n_frames", 1) > 1
        exif = image.getexif()
        suggestions = _suggestions(exif)
        orientation = _ORIENTATIONS.get(exif.get(ExifTags.Base.Orientation))
        icc = image.info.get("icc_profile") if image.mode in ("RGB", "RGBA") else None
        flat = _flatten(image)
        if animated:
            # The first frame alone becomes the original, losslessly, with no metadata.
            upright = flat.transpose(orientation) if orientation is not None else flat
            buffer = io.BytesIO()
            upright.save(buffer, "WEBP", lossless=True, icc_profile=icc)
            original, file_format = buffer.getvalue(), Format.WEBP
            del upright
        else:
            original = sanitise(data, file_format)
        source = _resized(flat, large)
        del flat  # the full-size bitmap goes with `image`, not at the return
    if orientation is not None:
        source = source.transpose(orientation)
        if orientation in _QUARTER_TURNS:
            size = size[::-1]
    return Processed(file_format, original, _renditions(source, size, cap, icc), suggestions)


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
    return Processed(Format.PDF, data, _renditions(preview, preview.size, cap, None), Suggestions())


# EXIF orientation to the transposition that makes the image upright, as `exif_transpose`.
_ORIENTATIONS = {
    2: Image.Transpose.FLIP_LEFT_RIGHT,
    3: Image.Transpose.ROTATE_180,
    4: Image.Transpose.FLIP_TOP_BOTTOM,
    5: Image.Transpose.TRANSPOSE,
    6: Image.Transpose.ROTATE_270,
    7: Image.Transpose.TRANSVERSE,
    8: Image.Transpose.ROTATE_90,
}
_QUARTER_TURNS = {
    Image.Transpose.TRANSPOSE,
    Image.Transpose.ROTATE_270,
    Image.Transpose.TRANSVERSE,
    Image.Transpose.ROTATE_90,
}
# The pixels of each band `_resized` reduces at a time: 16 MB in RGBA.
_BAND_PIXELS = 4_000_000


def _flatten(image: Image.Image) -> Image.Image:
    """RGB, or RGBA when the image has transparency: what WebP stores. No copy if it is."""
    transparent = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
    mode = "RGBA" if transparent else "RGB"
    return image if image.mode == mode else image.convert(mode)


def _fit(size: tuple[int, int], edge: int) -> tuple[int, int]:
    """`size` scaled so that its long edge is `edge`."""
    width, height = size
    scale = edge / max(width, height)
    return max(1, round(width * scale)), max(1, round(height * scale))


def _resized(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """A new image of `size`, resampled with Lanczos.

    Past twice `size`, it first reduces by an integer factor, a box filter, band by band:
    Pillow converts an image with alpha to premultiplied alpha before reducing it, which
    would be a second full-size bitmap. Bands whose height is a multiple of the factor
    give the same pixels as reducing the whole image.
    """
    width, height = image.size
    factor = min(width // size[0], height // size[1]) // 2
    if factor < 2:
        return image.resize(size, Image.Resampling.LANCZOS)
    reduced = Image.new(image.mode, (-(-width // factor), -(-height // factor)))
    band = factor * max(1, _BAND_PIXELS // (width * factor))
    for top in range(0, height, band):
        part = image.crop((0, top, width, min(top + band, height))).reduce(factor)
        reduced.paste(part, (0, top // factor))
    return reduced.resize(size, Image.Resampling.LANCZOS)


def _renditions(
    image: Image.Image, size: tuple[int, int], cap: int, icc: bytes | None
) -> dict[Rendition, tuple[bytes, int, int]]:
    """The renditions of a source of `size`, from `image`, its large rendition.

    Each derives from the next larger one, so that no full-size copy is ever made.
    """
    renditions = {}
    for rendition in (Rendition.LARGE, Rendition.VIEW, Rendition.THUMBNAIL):
        fitted = _fit(size, rendition_edge(rendition, cap, max(size)))
        if image.size != fitted:
            image = image.resize(fitted, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        # Only what is passed here is written: no EXIF, XMP, or IPTC.
        image.save(buffer, "WEBP", quality=WEBP_QUALITY, method=4, icc_profile=icc)
        renditions[rendition] = (buffer.getvalue(), *image.size)
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
