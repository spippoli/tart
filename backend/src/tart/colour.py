"""Colours: CSS colour literals and their WCAG 2.2 contrast.

    parse_colour("hsla(30, 20%, 90%, 0.5)") -> ("#EBE6E0", 0.5)   # or None
    contrast_ratio("#7A2E1C", "#FFFFFF") -> 9.40 (rounded)

Contrast compares opaque `#RRGGBB` colours. What lies under a translucent colour is
not known where it is checked, so `parse_colour` returns the alpha for the caller
to decide.
"""

import colorsys
import re

HEX_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _channel(value: int) -> float:
    srgb = value / 255
    return srgb / 12.92 if srgb <= 0.04045 else ((srgb + 0.055) / 1.055) ** 2.4


def relative_luminance(colour: str) -> float:
    if not HEX_COLOUR.match(colour):
        raise ValueError(f"{colour!r} is not a #RRGGBB colour")
    red, green, blue = (int(colour[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast_ratio(first: str, second: str) -> float:
    """The WCAG contrast ratio, from 1 (same luminance) to 21 (black on white)."""
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


# CSS Color Module Level 4 named colours.
_NAMED = {
    "aliceblue": "F0F8FF",
    "antiquewhite": "FAEBD7",
    "aqua": "00FFFF",
    "aquamarine": "7FFFD4",
    "azure": "F0FFFF",
    "beige": "F5F5DC",
    "bisque": "FFE4C4",
    "black": "000000",
    "blanchedalmond": "FFEBCD",
    "blue": "0000FF",
    "blueviolet": "8A2BE2",
    "brown": "A52A2A",
    "burlywood": "DEB887",
    "cadetblue": "5F9EA0",
    "chartreuse": "7FFF00",
    "chocolate": "D2691E",
    "coral": "FF7F50",
    "cornflowerblue": "6495ED",
    "cornsilk": "FFF8DC",
    "crimson": "DC143C",
    "cyan": "00FFFF",
    "darkblue": "00008B",
    "darkcyan": "008B8B",
    "darkgoldenrod": "B8860B",
    "darkgray": "A9A9A9",
    "darkgreen": "006400",
    "darkgrey": "A9A9A9",
    "darkkhaki": "BDB76B",
    "darkmagenta": "8B008B",
    "darkolivegreen": "556B2F",
    "darkorange": "FF8C00",
    "darkorchid": "9932CC",
    "darkred": "8B0000",
    "darksalmon": "E9967A",
    "darkseagreen": "8FBC8F",
    "darkslateblue": "483D8B",
    "darkslategray": "2F4F4F",
    "darkslategrey": "2F4F4F",
    "darkturquoise": "00CED1",
    "darkviolet": "9400D3",
    "deeppink": "FF1493",
    "deepskyblue": "00BFFF",
    "dimgray": "696969",
    "dimgrey": "696969",
    "dodgerblue": "1E90FF",
    "firebrick": "B22222",
    "floralwhite": "FFFAF0",
    "forestgreen": "228B22",
    "fuchsia": "FF00FF",
    "gainsboro": "DCDCDC",
    "ghostwhite": "F8F8FF",
    "gold": "FFD700",
    "goldenrod": "DAA520",
    "gray": "808080",
    "green": "008000",
    "greenyellow": "ADFF2F",
    "grey": "808080",
    "honeydew": "F0FFF0",
    "hotpink": "FF69B4",
    "indianred": "CD5C5C",
    "indigo": "4B0082",
    "ivory": "FFFFF0",
    "khaki": "F0E68C",
    "lavender": "E6E6FA",
    "lavenderblush": "FFF0F5",
    "lawngreen": "7CFC00",
    "lemonchiffon": "FFFACD",
    "lightblue": "ADD8E6",
    "lightcoral": "F08080",
    "lightcyan": "E0FFFF",
    "lightgoldenrodyellow": "FAFAD2",
    "lightgray": "D3D3D3",
    "lightgreen": "90EE90",
    "lightgrey": "D3D3D3",
    "lightpink": "FFB6C1",
    "lightsalmon": "FFA07A",
    "lightseagreen": "20B2AA",
    "lightskyblue": "87CEFA",
    "lightslategray": "778899",
    "lightslategrey": "778899",
    "lightsteelblue": "B0C4DE",
    "lightyellow": "FFFFE0",
    "lime": "00FF00",
    "limegreen": "32CD32",
    "linen": "FAF0E6",
    "magenta": "FF00FF",
    "maroon": "800000",
    "mediumaquamarine": "66CDAA",
    "mediumblue": "0000CD",
    "mediumorchid": "BA55D3",
    "mediumpurple": "9370DB",
    "mediumseagreen": "3CB371",
    "mediumslateblue": "7B68EE",
    "mediumspringgreen": "00FA9A",
    "mediumturquoise": "48D1CC",
    "mediumvioletred": "C71585",
    "midnightblue": "191970",
    "mintcream": "F5FFFA",
    "mistyrose": "FFE4E1",
    "moccasin": "FFE4B5",
    "navajowhite": "FFDEAD",
    "navy": "000080",
    "oldlace": "FDF5E6",
    "olive": "808000",
    "olivedrab": "6B8E23",
    "orange": "FFA500",
    "orangered": "FF4500",
    "orchid": "DA70D6",
    "palegoldenrod": "EEE8AA",
    "palegreen": "98FB98",
    "paleturquoise": "AFEEEE",
    "palevioletred": "DB7093",
    "papayawhip": "FFEFD5",
    "peachpuff": "FFDAB9",
    "peru": "CD853F",
    "pink": "FFC0CB",
    "plum": "DDA0DD",
    "powderblue": "B0E0E6",
    "purple": "800080",
    "rebeccapurple": "663399",
    "red": "FF0000",
    "rosybrown": "BC8F8F",
    "royalblue": "4169E1",
    "saddlebrown": "8B4513",
    "salmon": "FA8072",
    "sandybrown": "F4A460",
    "seagreen": "2E8B57",
    "seashell": "FFF5EE",
    "sienna": "A0522D",
    "silver": "C0C0C0",
    "skyblue": "87CEEB",
    "slateblue": "6A5ACD",
    "slategray": "708090",
    "slategrey": "708090",
    "snow": "FFFAFA",
    "springgreen": "00FF7F",
    "steelblue": "4682B4",
    "tan": "D2B48C",
    "teal": "008080",
    "thistle": "D8BFD8",
    "tomato": "FF6347",
    "turquoise": "40E0D0",
    "violet": "EE82EE",
    "wheat": "F5DEB3",
    "white": "FFFFFF",
    "whitesmoke": "F5F5F5",
    "yellow": "FFFF00",
    "yellowgreen": "9ACD32",
}

_HEX = re.compile(r"^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_FUNCTION = re.compile(r"^(rgba?|hsla?)\((.*)\)$")
_NUMBER = r"[+-]?(?:\d+\.?\d*|\.\d+)"
_COMPONENT = re.compile(rf"^({_NUMBER})(%|deg)?$")


def _components(arguments: str) -> list[tuple[float, str]] | None:
    # Both the legacy comma syntax and the space syntax with `/ alpha`.
    parts = re.split(r"\s*,\s*|\s*/\s*|\s+", arguments.strip())
    components = []
    for part in parts:
        match = _COMPONENT.match(part)
        if not match:
            return None
        components.append((float(match[1]), match[2] or ""))
    return components if len(components) in (3, 4) else None


def _alpha(component: tuple[float, str]) -> float:
    value, unit = component
    return value / 100 if unit == "%" else value


def _hex(red: float, green: float, blue: float) -> str:
    channels = (round(min(max(channel, 0), 1) * 255) for channel in (red, green, blue))
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def parse_colour(literal: str) -> tuple[str, float] | None:
    """The colour as `#RRGGBB` and its alpha (0 to 1), or `None` if it is not a CSS colour."""
    text = literal.strip().lower()
    if text == "transparent":
        return "#000000", 0.0
    if text in _NAMED:
        return f"#{_NAMED[text]}", 1.0
    if _HEX.match(text):
        digits = text[1:]
        if len(digits) in (3, 4):
            digits = "".join(digit * 2 for digit in digits)
        alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
        return f"#{digits[:6].upper()}", alpha
    function = _FUNCTION.match(text)
    if not function:
        return None
    components = _components(function[2])
    if components is None:
        return None
    alpha = min(max(_alpha(components[3]), 0), 1) if len(components) == 4 else 1.0
    if function[1].startswith("rgb"):
        channels = [value / 100 if unit == "%" else value / 255 for value, unit in components[:3]]
        if any(unit == "deg" for _, unit in components[:3]):
            return None
        return _hex(*channels), alpha
    (hue, hue_unit), (saturation, s_unit), (lightness, l_unit) = components[:3]
    if hue_unit == "%" or s_unit != "%" or l_unit != "%":
        return None
    red, green, blue = colorsys.hls_to_rgb((hue % 360) / 360, lightness / 100, saturation / 100)
    return _hex(red, green, blue), alpha
