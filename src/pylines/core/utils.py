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

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Literal

import pygame as pg
from pygame.surface import Surface

from .colours import WHITE
from .custom_types import AColour, Colour, Coord2, RealNumber


@dataclass
class Rotation:
    pitch: int
    yaw: int
    roll: int

def draw_text(surface: Surface, pos: tuple[float, float],
              horiz_align: Literal['left', 'centre', 'right'],
              vert_align: Literal['top', 'centre', 'bottom'],
              text: str, colour: Colour,
              font_size: int, font_family: pg.font.Font | Path | str | None = None):
    if isinstance(font_family, pg.font.Font):
        font_obj = font_family
    elif isinstance(font_family, (str, Path)):
        font_obj = pg.font.Font(str(font_family), font_size)
    else:
        font_obj = pg.font.Font(None, font_size)

    img = font_obj.render(text, True, colour)
    r = img.get_rect()

    # Horizontal
    if horiz_align == "left":
        setattr(r, "left", pos[0])
    elif horiz_align == "centre":
        setattr(r, "centerx", pos[0])
    elif horiz_align == "right":
        setattr(r, "right", pos[0])
    else:
        raise ValueError("Invalid horiz_align")

    # Vertical
    if vert_align == "top":
        setattr(r, "top", pos[1])
    elif vert_align == "centre":
        setattr(r, "centery", pos[1])
    elif vert_align == "bottom":
        setattr(r, "bottom", pos[1])
    else:
        raise ValueError("Invalid vert_align")

    surface.blit(img, r)

def draw_needle(surf: Surface, centre: Coord2, angle_deg: RealNumber, length: RealNumber, colour: Colour = (255, 0, 0), width: int = 3):
    angle_rad = math.radians(angle_deg)

    end = (
        centre[0] + math.cos(angle_rad) * length,
        centre[1] - math.sin(angle_rad) * length  # minus because screen Y is down
    )

    pg.draw.line(surf, colour, centre, end, width)

def frange(start: int | float, stop: int | float, step: int | float) -> Generator[float, None, None]:
    """A version of range that accepts and yields floats."""
    if step == 0:
        raise ValueError("step cannot be zero")

    current = start
    if step > 0:
        while current < stop:
            yield current
            current += step
    else:
        while current > stop:
            yield current
            current += step

def clamp(value: RealNumber, clamp_range: tuple[RealNumber, RealNumber]):
    lower, upper = clamp_range

    if any(math.isnan(x) for x in (value, lower, upper)):
        raise ValueError("NaN is not a valid input to clamp")
    if lower > upper:
        raise ValueError("upper bound must be greater than lower bound")  # keeps things consistent

    return max(lower, min(value, upper))

def draw_transparent_rect(surface: Surface, pos: Coord2, size: Coord2,
                          bg_colour: AColour = (0, 0, 0, 180),
                          border_thickness=0, border_colour: Colour = WHITE,
                          ):
    """Draws a semi-transparent rectangle with a border onto a surface.
    For a transparent rect only, set border thickness to 0."""
    box_surf = pg.Surface(size, pg.SRCALPHA)
    box_surf.fill(bg_colour)
    if border_thickness:
        pg.draw.rect(box_surf, border_colour, box_surf.get_rect(), border_thickness)
    surface.blit(box_surf, pos)

def get_sign(n: int | float):
    if not (isinstance(n, int) or isinstance(n, float)):
        raise ValueError("get sign: invalid number")

    return 1 if n > 0 else 0 if n == 0 else -1

def map_value(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """Maps a value from one range to another."""
    if in_min == in_max:
        return out_min

    range_scale_factor = (out_max - out_min) / (in_max - in_min)
    return range_scale_factor * (value - in_min) + out_min

# TODO: make a more universal unit_convert func, but this will do for now
def metres_to_ft(value: RealNumber) -> RealNumber:
    """Convert a distance in metres to feet"""
    return value * 3.280839895

# For debug only
def _prettyvec(vec: pg.Vector3, dp: int = 3) -> str:
    return f"({vec.x:,.{dp}f}, {vec.y:,.{dp}f}, {vec.z:,.{dp}f})"