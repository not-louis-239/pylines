"""Defined colours for the program"""

from dataclasses import dataclass
from core.custom_types import Colour

@dataclass(frozen=True)
class ColourScheme:
    high: Colour
    mid: Colour
    low: Colour

def _hex_to_rgb(hex_col: str) -> Colour:
    """Internal function to convert HEX colours to RGB."""
    h = hex_col.lstrip('#')

    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)

    return (r, g, b)

WHITE = (255, 255, 255)

# Sky colours
SKY_COLOUR_SCHEMES: dict[str, ColourScheme] = {
    "night": ColourScheme(
        _hex_to_rgb("#100B26"),
        _hex_to_rgb("#3F1759"),
        _hex_to_rgb("#9E3F9B")
    ),
    "sunrise": ColourScheme(
        _hex_to_rgb("#1C456E"),
        _hex_to_rgb("#82AABC"),
        _hex_to_rgb("#F7FF56")
    ),
    "day": ColourScheme(
        _hex_to_rgb("#4179D3"),
        _hex_to_rgb("#73B5EE"),
        _hex_to_rgb("#9CFCFB")
    ),
    "sunset": ColourScheme(
        _hex_to_rgb("#6B496C"),
        _hex_to_rgb("#D22A2A"),
        _hex_to_rgb("#E3B153")
    )
}