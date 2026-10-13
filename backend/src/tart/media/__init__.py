"""The media pipeline (Foundations spec, 3. Storage and media pipeline; ADR 0004, ADR 0012).

    POST /api/media        one file per request, streamed into quarantine (`tart.api.media`)
      -> process_upload    in the worker: detect, decode, sanitise, derive (`uploads`)
      -> permanent area    media/<id>/original and one WebP object per rendition
    hourly sweep           deletes uploads never attached, 24 hours after upload

An upload's id names its objects; a Documentation item's `file` holds that id.
Refusals carry a translatable error code.
"""

from enum import StrEnum

MAX_PIXELS = 100_000_000
"""The pixel limit of an image or a PDF preview, a platform constant, enforced as an error."""
MULTIPART_MARGIN_MB = 1
"""What Caddy allows above `max_upload_mb` for the multipart framing; the app checks the file."""

FILE_TOO_LARGE = "file_too_large"
ONE_FILE_PER_REQUEST = "one_file_per_request"
FILE_MISSING = "file_missing"
FILE_TYPE_UNSUPPORTED = "file_type_unsupported"
FILE_UNREADABLE = "file_unreadable"
IMAGE_TOO_LARGE = "image_too_large"
UPLOAD_NOT_FOUND = "upload_not_found"


class Format(StrEnum):
    """The accepted file types, a platform constant; GIF and TIFF are refused."""

    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    AVIF = "avif"
    HEIC = "heic"
    PDF = "pdf"


class Rendition(StrEnum):
    """The public renditions, all WebP, by long edge."""

    THUMBNAIL = "thumbnail"
    VIEW = "view"
    LARGE = "large"


RENDITION_EDGES = {Rendition.THUMBNAIL: 480, Rendition.VIEW: 1280}
"""Platform constants; `large` is the Instance's `media.public_rendition_max_px`."""


def rendition_edge(rendition: Rendition, cap: int, long_edge: int) -> int:
    """The long edge of a rendition: its size, never above the cap nor the source's own."""
    return min(RENDITION_EDGES.get(rendition, cap), cap, long_edge)


def quarantine_key(upload_id: str) -> str:
    return f"uploads/{upload_id}"


def original_key(upload_id: str) -> str:
    return f"media/{upload_id}/original"


def rendition_key(upload_id: str, rendition: Rendition) -> str:
    return f"media/{upload_id}/{rendition.value}"
