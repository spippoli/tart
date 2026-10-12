"""Strip GPS and device identifiers from a stored original, leaving its image data as it is
(Foundations spec, 3, step 4; ADR 0012).

Nothing is re-encoded: the EXIF and XMP blocks are blanked in place, so every offset in
the file stays valid and the pixels are those that were uploaded.

- EXIF: the GPS directory is emptied; the device tags (make, model, serial numbers,
  owner, maker note, ...) are zeroed. Orientation, dates, and exposure stay.
- XMP: the packet is replaced by an empty one of the same length, since XMP repeats the
  GPS position and device serials in its own vocabulary.
- JPEG: data after the main image's end (secondary images of a Multi-Picture file, each
  with its own EXIF) is cut, and the Multi-Picture index is zeroed.
- PNG: text chunks are dropped (XMP and the "Raw profile" EXIF of some tools live there).

A block that cannot be parsed is zeroed whole.
"""

import struct
import zlib
from collections.abc import Iterator

from tart.media import Format

_GPS_IFD = 0x8825
_EXIF_IFD = 0x8769
_DEVICE_TAGS = frozenset(
    {
        0x010F,  # Make
        0x0110,  # Model
        0x0131,  # Software
        0x013C,  # HostComputer
        0x927C,  # MakerNote
        0xA420,  # ImageUniqueID
        0xA430,  # CameraOwnerName
        0xA431,  # BodySerialNumber
        0xA433,  # LensMake
        0xA434,  # LensModel
        0xA435,  # LensSerialNumber
        0xC614,  # UniqueCameraModel
        0xC62F,  # CameraSerialNumber
    }
)
# Bytes per value of each TIFF field type (TIFF 6.0 and its later additions).
_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 13: 4}
_EXIF_PREFIX = b"Exif\x00\x00"
_XMP_PREFIX = b"http://ns.adobe.com/xap/1.0/\x00"
_XMP_EXTENSION_PREFIX = b"http://ns.adobe.com/xmp/extension/\x00"
_EMPTY_XMP = (
    b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?><x:xmpmeta xmlns:x="adobe:ns:meta/"/>',
    b'<?xpacket end="w"?>',
)


class SanitiseError(ValueError):
    """The file's structure is broken where its metadata should be."""


def sanitise(data: bytes, file_format: Format) -> bytes:
    """The file without GPS or device identifiers; PDFs are returned as they are."""
    match file_format:
        case Format.JPEG:
            return _jpeg(bytearray(data))
        case Format.PNG:
            return _png(data)
        case Format.WEBP:
            return _webp(bytearray(data))
        case Format.AVIF | Format.HEIC:
            return _heif(bytearray(data))
        case Format.PDF:
            return data


# EXIF and XMP blocks.


def blank_exif(buffer: bytearray, start: int, end: int) -> None:
    """Blank the GPS and device tags of the TIFF structure at `buffer[start:end]`."""
    try:
        _blank_tiff(memoryview(buffer)[start:end])
    except IndexError, struct.error, SanitiseError:
        buffer[start:end] = bytes(end - start)


def _blank_tiff(tiff: memoryview) -> None:
    order = {b"II": "<", b"MM": ">"}.get(bytes(tiff[:2]))
    if order is None or struct.unpack_from(order + "H", tiff, 2)[0] != 42:
        raise SanitiseError("not a TIFF header")
    seen: set[int] = set()

    def walk(offset: int, *, gps: bool = False) -> int:
        """Blank one directory; returns the offset of the next one, or 0."""
        if offset in seen or not 8 <= offset < len(tiff):
            raise SanitiseError("directory loop or out of bounds")
        seen.add(offset)
        (count,) = struct.unpack_from(order + "H", tiff, offset)
        end = offset + 2 + 12 * count
        (following,) = struct.unpack_from(order + "I", tiff, end)
        for entry in range(offset + 2, end, 12):
            tag, kind, values, pointer = struct.unpack_from(order + "HHII", tiff, entry)
            if tag in (_EXIF_IFD, _GPS_IFD) and not gps:
                walk(pointer, gps=tag == _GPS_IFD)
            elif gps or tag in _DEVICE_TAGS:
                size = _TYPE_SIZES.get(kind, 1) * values
                if size > 4:
                    if pointer + size > len(tiff):
                        raise SanitiseError("value out of bounds")
                    tiff[pointer : pointer + size] = bytes(size)
                else:
                    tiff[entry + 8 : entry + 12] = bytes(4)
        if gps:
            # An empty directory: no entries and no next directory.
            tiff[offset : end + 4] = bytes(end + 4 - offset)
        return following

    following = walk(struct.unpack_from(order + "I", tiff, 4)[0])
    if following:  # IFD1, the embedded thumbnail's directory
        walk(following)


def blank_xmp(buffer: bytearray, start: int, end: int) -> None:
    """Replace the XMP packet at `buffer[start:end]` by an empty one of the same length."""
    head, tail = _EMPTY_XMP
    padding = end - start - len(head) - len(tail)
    buffer[start:end] = head + b" " * padding + tail if padding >= 0 else b" " * (end - start)


# Containers.


def _jpeg(buffer: bytearray) -> bytes:
    for marker, start, end in _jpeg_segments(buffer):
        payload = buffer[start:end]
        if marker == 0xE1 and payload.startswith(_EXIF_PREFIX):
            blank_exif(buffer, start + len(_EXIF_PREFIX), end)
        elif marker == 0xE1 and payload.startswith(_XMP_PREFIX):
            blank_xmp(buffer, start + len(_XMP_PREFIX), end)
        elif marker == 0xE1 and payload.startswith(_XMP_EXTENSION_PREFIX):
            # A GUID, the full length, and the offset (40 bytes), then part of a packet.
            buffer[start + len(_XMP_EXTENSION_PREFIX) + 40 : end] = b" " * max(
                0, end - start - len(_XMP_EXTENSION_PREFIX) - 40
            )
        elif marker == 0xE2 and payload.startswith(b"MPF\x00"):
            buffer[start:end] = bytes(end - start)
        elif marker == 0xD9:
            return bytes(buffer[:end])
    raise SanitiseError("no end of image")


def _jpeg_segments(data: bytearray) -> Iterator[tuple[int, int, int]]:
    """Each marker with its payload's span, up to and including the end of image."""
    position = 2
    while position < len(data):
        if data[position] != 0xFF:
            raise SanitiseError("marker expected")
        marker = data[position + 1]
        if marker == 0xFF:  # fill byte
            position += 1
            continue
        if marker == 0xD9:
            yield marker, position + 2, position + 2
            return
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            position += 2
            continue
        (length,) = struct.unpack_from(">H", data, position + 2)
        start, end = position + 4, position + 2 + length
        if length < 2 or end > len(data):
            raise SanitiseError("segment out of bounds")
        yield marker, start, end
        position = end
        if marker == 0xDA:  # entropy-coded data runs to the next marker
            while position + 1 < len(data) and not (
                data[position] == 0xFF and data[position + 1] not in (0x00, *range(0xD0, 0xD8))
            ):
                position += 1


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_TEXT = {b"tEXt", b"zTXt", b"iTXt"}


def _png(data: bytes) -> bytes:
    output = bytearray(_PNG_SIGNATURE)
    position = len(_PNG_SIGNATURE)
    while position + 8 <= len(data):
        length, kind = struct.unpack_from(">I4s", data, position)
        end = position + 12 + length
        if end > len(data):
            raise SanitiseError("chunk out of bounds")
        if kind == b"eXIf":
            chunk = bytearray(data[position:end])
            blank_exif(chunk, 8, 8 + length)
            chunk[-4:] = struct.pack(">I", zlib.crc32(chunk[4:-4]))
            output += chunk
        elif kind not in _PNG_TEXT:
            output += data[position:end]
        position = end
        if kind == b"IEND":
            return bytes(output)
    raise SanitiseError("no IEND chunk")


def _webp(buffer: bytearray) -> bytes:
    end = 8 + int.from_bytes(buffer[4:8], "little")
    if end > len(buffer):
        raise SanitiseError("RIFF out of bounds")
    position = 12
    while position + 8 <= end:
        kind = bytes(buffer[position : position + 4])
        size = int.from_bytes(buffer[position + 4 : position + 8], "little")
        start, stop = position + 8, position + 8 + size
        if stop > end:
            raise SanitiseError("chunk out of bounds")
        if kind == b"EXIF":
            skip = len(_EXIF_PREFIX) if buffer[start:stop].startswith(_EXIF_PREFIX) else 0
            blank_exif(buffer, start + skip, stop)
        elif kind == b"XMP ":
            blank_xmp(buffer, start, stop)
        position = stop + (size & 1)  # chunks are padded to an even size
    return bytes(buffer[:end])


def _heif(buffer: bytearray) -> bytes:
    """AVIF and HEIC: blank every `Exif` item and every XMP (`mime`) item in place."""
    meta = _child(buffer, 0, len(buffer), b"meta")
    if meta is None:
        return bytes(buffer)
    start, end = meta[0] + 4, meta[1]  # a full box: version and flags first
    kinds = _item_kinds(buffer, _child(buffer, start, end, b"iinf"))
    idat = _child(buffer, start, end, b"idat")
    for item_id, extents in _item_locations(buffer, _child(buffer, start, end, b"iloc"), idat):
        kind = kinds.get(item_id)
        if kind not in (b"Exif", b"mime"):
            continue
        if len(extents) != 1:
            for offset, length in extents:
                buffer[offset : offset + length] = bytes(length)
            continue
        ((offset, length),) = extents
        if offset + length > len(buffer):
            raise SanitiseError("item out of bounds")
        if kind == b"Exif":
            # A 4-byte offset to the TIFF header, which may follow an "Exif\0\0" prefix.
            header = 4 + int.from_bytes(buffer[offset : offset + 4])
            blank_exif(buffer, offset + header, offset + length)
        elif buffer[offset : offset + length].lstrip().startswith((b"<?xpacket", b"<x:xmpmeta")):
            blank_xmp(buffer, offset, offset + length)
    return bytes(buffer)


def _boxes(data: bytearray, start: int, end: int) -> Iterator[tuple[bytes, int, int]]:
    """Each box in `data[start:end]` as its type and its content's span."""
    position = start
    while position + 8 <= end:
        size = int.from_bytes(data[position : position + 4])
        kind = bytes(data[position + 4 : position + 8])
        header = 8
        if size == 1:
            size = int.from_bytes(data[position + 8 : position + 16])
            header = 16
        elif size == 0:
            size = end - position
        if size < header or position + size > end:
            raise SanitiseError("box out of bounds")
        yield kind, position + header, position + size
        position += size


def _child(data: bytearray, start: int, end: int, kind: bytes) -> tuple[int, int] | None:
    return next(((s, e) for k, s, e in _boxes(data, start, end) if k == kind), None)


def _item_kinds(data: bytearray, iinf: tuple[int, int] | None) -> dict[int, bytes]:
    """Item ids and their types, from the item information box."""
    if iinf is None:
        return {}
    start, end = iinf
    version = data[start]
    first = start + 4 + (2 if version == 0 else 4)
    kinds = {}
    for kind, entry, entry_end in _boxes(data, first, end):
        if kind != b"infe" or data[entry] < 2:
            continue
        id_size = 2 if data[entry] == 2 else 4
        item_id = int.from_bytes(data[entry + 4 : entry + 4 + id_size])
        type_at = entry + 4 + id_size + 2
        if type_at + 4 <= entry_end:
            kinds[item_id] = bytes(data[type_at : type_at + 4])
    return kinds


def _item_locations(
    data: bytearray, iloc: tuple[int, int] | None, idat: tuple[int, int] | None
) -> Iterator[tuple[int, list[tuple[int, int]]]]:
    """Each item's extents as file offsets and lengths, from the item location box."""
    if iloc is None:
        return
    start, _ = iloc
    version = data[start]
    position = start + 4

    def number(size: int) -> int:
        nonlocal position
        value = int.from_bytes(data[position : position + size])
        position += size
        return value

    sizes = number(2)
    offset_size, length_size = sizes >> 12, (sizes >> 8) & 0xF
    base_offset_size, index_size = (sizes >> 4) & 0xF, sizes & 0xF
    count = number(2 if version < 2 else 4)
    for _ in range(count):
        item_id = number(2 if version < 2 else 4)
        construction = number(2) & 0xF if version in (1, 2) else 0
        number(2)  # data reference index
        base = number(base_offset_size)
        extents = []
        for _ in range(number(2)):
            if version in (1, 2) and index_size:
                number(index_size)
            extent_offset, extent_length = number(offset_size), number(length_size)
            extents.append((base + extent_offset, extent_length))
        if construction == 0:
            yield item_id, extents
        elif construction == 1 and idat is not None:
            yield item_id, [(idat[0] + offset, length) for offset, length in extents]
