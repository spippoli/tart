"""Foundations spec, 3. Storage and media pipeline, Processing: criteria 23 to 27.

The processing function fed the fixture files of the Testing Decisions, with assertions on
what it gives to store: the original, the renditions, the suggestions, or an error code.
"""

import io

import pytest
from media_fixtures import (
    CAPTURE_DATE,
    HEIC_WITH_GPS,
    LATITUDE,
    LONGITUDE,
    SERIAL,
    animated_webp,
    avif_with_gps,
    decompression_bomb,
    encode,
    jpeg_with_gps,
    pdf,
    picture,
    png_header_only,
    png_with_gps,
    webp_with_gps,
)
from PIL import ExifTags, Image

from tart.media import (
    FILE_TYPE_UNSUPPORTED,
    FILE_UNREADABLE,
    IMAGE_TOO_LARGE,
    Format,
    Rendition,
)
from tart.media.processing import Processed, Rejected, process

CAP = 2048
DEVICE_TAGS = (ExifTags.Base.Make, ExifTags.Base.Model)


def _processed(data: bytes, cap: int = CAP) -> Processed:
    result = process(data, cap)
    assert isinstance(result, Processed), result
    return result


def _open(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    image.load()
    return image


def _assert_no_position_or_device(original: bytes) -> None:
    image = _open(original)
    found = image.getexif()
    assert found.get_ifd(ExifTags.IFD.GPSInfo) == {}
    for tag in DEVICE_TAGS:
        assert not str(found.get(tag, "")).strip("\x00")
    details = found.get_ifd(ExifTags.IFD.Exif)
    assert not str(details.get(ExifTags.Base.BodySerialNumber, "")).strip("\x00")
    assert SERIAL.encode() not in original
    assert b"GPSLatitude" not in original
    assert b"FictionalCam" not in original


def _assert_no_metadata(rendition: bytes) -> None:
    image = _open(rendition)
    assert image.format == "WEBP"
    assert "exif" not in image.info
    assert "xmp" not in image.info
    assert not image.getexif()


FILES_WITH_GPS = {
    "jpeg": (jpeg_with_gps, Format.JPEG),
    "png": (png_with_gps, Format.PNG),
    "webp": (webp_with_gps, Format.WEBP),
    "avif": (avif_with_gps, Format.AVIF),
    "heic": (HEIC_WITH_GPS.read_bytes, Format.HEIC),
}


@pytest.mark.parametrize("name", FILES_WITH_GPS)
def test_criterion_24_the_original_keeps_no_gps_or_device_identifiers(name: str) -> None:
    make, file_format = FILES_WITH_GPS[name]
    uploaded = make()

    result = _processed(uploaded)

    assert result.format is file_format
    _assert_no_position_or_device(result.original)
    # The image data is the uploaded one: nothing was re-encoded.
    assert _open(result.original).tobytes() == _open(uploaded).tobytes()
    assert len(result.original) <= len(uploaded)


@pytest.mark.parametrize("name", FILES_WITH_GPS)
def test_criterion_24_renditions_carry_no_exif_xmp_or_iptc(name: str) -> None:
    result = _processed(FILES_WITH_GPS[name][0]())

    assert set(result.renditions) == set(Rendition)
    for data, _, _ in result.renditions.values():
        _assert_no_metadata(data)


def test_criterion_24_exif_orientation_is_applied_to_the_renditions() -> None:
    # Orientation 6: stored landscape, to be shown turned 90° clockwise.
    result = _processed(jpeg_with_gps(400, 300, orientation=6))

    data, width, height = result.renditions[Rendition.THUMBNAIL]
    assert (width, height) == (300, 400)
    shown = _open(data).convert("RGB")
    assert shown.size == (300, 400)
    # The stored left half (red) is the top once turned.
    assert shown.getpixel((150, 20))[0] > 200
    assert shown.getpixel((150, 380))[0] < 60
    # The original keeps its orientation tag, so it still shows the right way up.
    assert _open(result.original).getexif()[ExifTags.Base.Orientation] == 6


def test_criterion_25_no_rendition_exceeds_the_cap() -> None:
    result = _processed(encode(picture(6000, 4000), "JPEG"), cap=1000)

    sizes = {rendition: (w, h) for rendition, (_, w, h) in result.renditions.items()}
    assert sizes == {
        Rendition.THUMBNAIL: (480, 320),
        Rendition.VIEW: (1000, 667),
        Rendition.LARGE: (1000, 667),
    }
    for data, width, height in result.renditions.values():
        assert max(_open(data).size) <= 1000
        assert _open(data).size == (width, height)


def test_criterion_26_the_capture_date_and_position_are_only_suggested() -> None:
    result = _processed(jpeg_with_gps())

    assert result.suggestions.observed_date == CAPTURE_DATE
    assert result.suggestions.point == pytest.approx((LONGITUDE, LATITUDE), abs=1e-4)


def test_criterion_26_heic_suggestions_come_from_its_exif() -> None:
    result = _processed(HEIC_WITH_GPS.read_bytes())

    assert result.suggestions.observed_date == "2024-11-20"
    assert result.suggestions.point == pytest.approx((LONGITUDE, LATITUDE), abs=1e-4)


def test_a_file_without_exif_suggests_nothing() -> None:
    result = _processed(encode(picture(100, 100), "PNG"))

    assert result.suggestions.observed_date is None
    assert result.suggestions.point is None


def test_criterion_27_renditions_by_long_edge() -> None:
    result = _processed(encode(picture(4000, 3000), "JPEG"))

    sizes = {rendition: (w, h) for rendition, (_, w, h) in result.renditions.items()}
    assert sizes == {
        Rendition.THUMBNAIL: (480, 360),
        Rendition.VIEW: (1280, 960),
        Rendition.LARGE: (2048, 1536),
    }


def test_criterion_27_no_rendition_is_upscaled() -> None:
    result = _processed(encode(picture(900, 600), "PNG"))

    sizes = {rendition: (w, h) for rendition, (_, w, h) in result.renditions.items()}
    assert sizes == {
        Rendition.THUMBNAIL: (480, 320),
        Rendition.VIEW: (900, 600),
        Rendition.LARGE: (900, 600),
    }


def test_criterion_27_a_pdf_gets_a_first_page_preview_and_its_renditions() -> None:
    uploaded = pdf()

    result = _processed(uploaded)

    assert result.format is Format.PDF
    assert result.original == uploaded
    sizes = {rendition: (w, h) for rendition, (_, w, h) in result.renditions.items()}
    # An A4 page, its long edge at the cap.
    assert sizes[Rendition.LARGE][1] == CAP
    assert sizes[Rendition.VIEW][1] == 1280
    assert sizes[Rendition.THUMBNAIL][1] == 480
    preview = _open(result.renditions[Rendition.VIEW][0]).convert("RGB")
    assert preview.getpixel((100, 640))[0] > 200  # the page's red half


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("gif", encode(picture(50, 50), "GIF")),
        ("tiff", encode(picture(50, 50), "TIFF")),
    ],
)
def test_criterion_27_gif_and_tiff_are_refused(name: str, data: bytes) -> None:
    assert process(data, CAP) == Rejected(FILE_TYPE_UNSUPPORTED)


@pytest.mark.filterwarnings("ignore::PIL.Image.DecompressionBombWarning")
def test_criterion_27_an_image_over_100_megapixels_is_refused() -> None:
    # 12 000 by 9 000 is 108 megapixels; 10 000 by 10 001 is just past the limit.
    assert process(png_header_only(12_000, 9_000), CAP) == Rejected(IMAGE_TOO_LARGE)
    assert process(png_header_only(10_000, 10_001), CAP) == Rejected(IMAGE_TOO_LARGE)


def test_a_decompression_bomb_is_refused() -> None:
    bomb = decompression_bomb()
    assert len(bomb) < 1_000_000

    assert process(bomb, CAP) == Rejected(IMAGE_TOO_LARGE)


def test_criterion_23_a_truncated_file_is_refused() -> None:
    whole = jpeg_with_gps(800, 600)

    assert process(whole[: len(whole) // 2], CAP) == Rejected(FILE_UNREADABLE)


def test_criterion_23_a_file_that_is_not_a_supported_type_is_refused() -> None:
    for data in (b"Not an image at all.", b"", b"<svg xmlns='http://www.w3.org/2000/svg'/>"):
        assert process(data, CAP) == Rejected(FILE_TYPE_UNSUPPORTED)


def test_criterion_23_content_that_lies_about_its_type_does_not_decode() -> None:
    # JPEG's first bytes, then something else entirely.
    assert process(b"\xff\xd8\xff\xe0" + b"\x00" * 200, CAP) == Rejected(FILE_UNREADABLE)
    # A PDF header with no document behind it.
    assert process(b"%PDF-1.7\nnothing here", CAP) == Rejected(FILE_UNREADABLE)


def test_the_type_comes_from_the_content() -> None:
    # The API never sees a name here: a PNG is a PNG whatever it was called.
    assert _processed(encode(picture(64, 64), "PNG")).format is Format.PNG
    assert _processed(encode(picture(64, 64), "WEBP")).format is Format.WEBP


def test_an_animated_webp_keeps_only_its_first_frame() -> None:
    result = _processed(animated_webp())

    original = _open(result.original)
    assert getattr(original, "n_frames", 1) == 1
    red, green, blue = original.convert("RGB").getpixel((10, 10))
    assert red > 245 and green < 10 and blue < 10
    thumbnail = _open(result.renditions[Rendition.THUMBNAIL][0]).convert("RGB")
    assert thumbnail.getpixel((10, 10))[0] > 200
