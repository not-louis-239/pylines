# Copyright 2025-2026 Louis Masarei-Boulton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Defined colours for the program"""

from dataclasses import dataclass
from typing import cast, overload

from .custom_types import Colour, AColour


@dataclass(frozen=True)
class ColourScheme:
    high: Colour
    mid: Colour
    low: Colour

@overload
def lerp_colours(c1: Colour, c2: Colour, t: float) -> Colour: ...
@overload
def lerp_colours(c1: AColour, c2: AColour, t: float) -> AColour: ...
def lerp_colours(c1: Colour | AColour, c2: Colour | AColour, t: float) -> Colour | AColour:
    def _lerp_colours(left: Colour, right: Colour, t: float) -> Colour:
        return (
            int(left[0] + (right[0] - left[0]) * t),
            int(left[1] + (right[1] - left[1]) * t),
            int(left[2] + (right[2] - left[2]) * t),
        )

    def _lerp_acolours(left: AColour, right: AColour, t: float) -> AColour:
        return (
            int(left[0] + (right[0] - left[0]) * t),
            int(left[1] + (right[1] - left[1]) * t),
            int(left[2] + (right[2] - left[2]) * t),
            int(left[3] + (right[3] - left[3]) * t),
        )

    if len(c1) == 3 and len(c2) == 3:
        return _lerp_colours(cast(Colour, c1), cast(Colour, c2), t)

    if len(c1) == 4 and len(c2) == 4:
        return _lerp_acolours(cast(AColour, c1), cast(AColour, c2), t)

    raise TypeError("lerp_colours expects both colours to have matching RGB or RGBA channels.")

def _hex_to_rgb(hex_col: str) -> Colour:
    """Internal function to convert HEX colours to RGB."""
    h = hex_col.lstrip('#')

    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)

    return (r, g, b)

# Sky colours
SKY_COLOUR_SCHEMES: dict[str, ColourScheme] = {
    "night": ColourScheme(
        _hex_to_rgb("#0A061D"),
        _hex_to_rgb("#200831"),
        _hex_to_rgb("#41163F")
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
        _hex_to_rgb("#EBA442"),
        _hex_to_rgb("#FFD68A")
    )
}

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

BLUE = (179, 228, 255)
BROWN = (255, 206, 173)
DARK_BLUE = (140, 208, 255)
DARK_BROWN = (200, 125, 80)

MAP_BORDER_COLOUR = (129, 137, 143)
MAP_RUNWAY_COLOUR = (175, 175, 175)
MAP_PROHIBITED_FILL_COLOR = (255, 0, 0, 51)
MAP_PROHIBITED_BORDER_COLOR = (255, 0, 0, 255)
MAP_PROHIBITED_TEXT_COLOUR = (255, 210, 210)
