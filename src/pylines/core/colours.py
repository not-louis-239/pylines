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

"""Defined colours for the program"""

from dataclasses import dataclass
from typing import cast, overload

from .custom_types import AColour, Colour

@dataclass(frozen=True)
class ColourScheme:
    high: Colour
    mid: Colour
    low: Colour

def lerp_colour(c1: Colour, c2: Colour, t: float) -> Colour:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))  # type: ignore[arg-type]

def _hex_to_rgb(hex_col: str) -> Colour:
    """Internal function to convert HEX colours to RGB."""
    h = hex_col.lstrip('#')

    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)

    return (r, g, b)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

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
DARK_BLUE = (140, 208, 255)
DARK_BROWN = (200, 125, 80)
