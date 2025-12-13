"""Defined colours for the program"""

from typing import overload, cast
from dataclasses import dataclass
from core.custom_types import Colour, AColour

@dataclass(frozen=True)
class ColourScheme:
    high: Colour
    mid: Colour
    low: Colour

@overload
def interpolate_cols(col1: Colour, col2: Colour, coeff: float) -> Colour: ...
@overload
def interpolate_cols(col1: AColour, col2: AColour, coeff: float) -> AColour: ...
def interpolate_cols(col1: Colour | AColour, col2: Colour | AColour, coeff: float = 0.5) -> Colour | AColour:
    """Returns a weighted average between col1 and col2.

    Coefficient = 0 -> returns col1
    Coefficient = 1 -> returns col2
    Linear interpolation in between."""

    def _is_colour(colour: object, col_type: type = Colour) -> bool:
        if col_type == Colour:
            return isinstance(colour, tuple) and len(colour) == 3 and all(isinstance(x, int) for x in colour)
        elif col_type == AColour:
            return isinstance(colour, tuple) and len(colour) == 4 and all(isinstance(x, int) for x in colour)
        return False

    if not 0 <= coeff <= 1:
        raise ValueError("interpolation coefficient must be between 0 and 1")

    if _is_colour(col1) and _is_colour(col2):
        r = round(col1[0] * (1 - coeff) + col2[0] * coeff)
        g = round(col1[1] * (1 - coeff) + col2[1] * coeff)
        b = round(col1[2] * (1 - coeff) + col2[2] * coeff)
        return (r, g, b)

    elif _is_colour(col1, AColour) and _is_colour(col2, AColour):
        col1, col2 = cast(AColour, col1), cast(AColour, col2)
        r = round(col1[0] * (1 - coeff) + col2[0] * coeff)
        g = round(col1[1] * (1 - coeff) + col2[1] * coeff)
        b = round(col1[2] * (1 - coeff) + col2[2] * coeff)
        alpha = round(col1[3] * (1 - coeff) + col2[3] * coeff)
        return (r, g, b, alpha)

    raise TypeError("colours must be of same type")

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
        _hex_to_rgb("#CD6464"),
        _hex_to_rgb("#E3B153")
    )
}

BLUE = (179, 228, 255)
BROWN = (255, 206, 173)