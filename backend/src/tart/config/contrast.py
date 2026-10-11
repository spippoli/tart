"""WCAG 2.2 contrast between two sRGB colours written as `#RRGGBB`."""

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
