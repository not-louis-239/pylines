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

import math
from math import cos, sin
from pathlib import Path
from typing import Literal

import pygame as pg
from pygame.surface import Surface

import pylines.core.constants as C
from .colours import WHITE
from .custom_types import AColour, Colour, Coord2, RealNumber


def draw_text(
        surface: Surface, pos: tuple[float, float],
        horiz_align: Literal['left', 'centre', 'right'],
        vert_align: Literal['top', 'centre', 'bottom'],
        text: str, colour: Colour | AColour,
        font_size: int, font_family: pg.font.Font | Path | str | None = None,
        rotation: float = 0
    ) -> None:
    if isinstance(font_family, pg.font.Font):
        font_obj = font_family
    elif isinstance(font_family, (str, Path)):
        font_obj = pg.font.Font(str(font_family), font_size)
    else:
        font_obj = pg.font.Font(None, font_size)

    img = font_obj.render(text, True, colour)
    if rotation != 0:
        img = pg.transform.rotate(img, rotation)
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

def frange(start, stop=None, step=1.0):
    """
    Float-based range generator.
    Behaves like range(start, stop, step) but accepts floats.
    """
    if stop is None:
        stop = float(start)
        start = 0.0

    current = float(start)
    step = float(step)

    if step == 0:
        raise ValueError("frange() arg 3 must not be zero")

    if step > 0:
        while current < stop:
            yield current
            current += step
    else:
        while current > stop:
            yield current
            current += step

def clamp(value: RealNumber, clamp_range: tuple[RealNumber, RealNumber], /) -> RealNumber:
    lower, upper = clamp_range

    if any(math.isnan(x) for x in (value, lower, upper)):
        raise ValueError("NaN is not a valid input to clamp")
    if lower > upper:
        raise ValueError("upper bound must be greater than lower bound")  # keeps things consistent

    return max(lower, min(value, upper))

def draw_transparent_rect(
        surface: Surface, pos: Coord2, size: Coord2,
        bg_colour: AColour = (0, 0, 0, 180),
        border_thickness=0, border_colour: Colour = WHITE,
    ) -> None:
    """Draws a semi-transparent rectangle with a border onto a surface.
    For a transparent rect only, set border thickness to 0."""
    box_surf = pg.Surface(size, pg.SRCALPHA)
    box_surf.fill(bg_colour)
    if border_thickness:
        pg.draw.rect(box_surf, border_colour, box_surf.get_rect(), border_thickness)
    surface.blit(box_surf, pos)

def get_sign(n: int | float, /) -> int:
    """Returns the sign of a number: 1 for positive, -1 for negative, 0 for zero."""
    if not (isinstance(n, int) or isinstance(n, float)):
        raise ValueError("get sign: not a number")

    return 1 if n > 0 else 0 if n == 0 else -1

def map_value(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """Maps a value from one range to another."""
    if in_min == in_max:
        return out_min

    range_scale_factor = (out_max - out_min) / (in_max - in_min)
    return range_scale_factor * (value - in_min) + out_min

def point_in_aabb(
        x: float, z: float,
        rx: float, rz: float, rl: float, rw: float, rotation_deg: float
    ) -> tuple[bool, tuple[float, float]]:

    # XXX: length and width may be swapped around in this func
    #      it might be faulty
    """
    Check if point (x, z) is inside a rotated rectangle (AABB in local space).

    Args:
        x, z: coordinates of the point
        rx, rz: rectangle centre coordinates
        rl, rw: rectangle length (along local x), width (along local z)
        rotation_deg: clockwise rotation of rectangle in degrees (0 = aligned with world axes)

    Returns:
        True if point is inside the rectangle, False otherwise
        distance in rectangle's local space
    """
    # Translate point to rectangle centre
    dx = x - rx
    dz = z - rz
    theta = math.radians(rotation_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    # Convert rotation to radians, clockwise
    theta = math.radians(rotation_deg)

    local_x = dx * cos_t + dz * sin_t
    local_z = -dx * sin_t + dz * cos_t
    half_length = rl / 2
    half_width = rw / 2

    inside = abs(local_x) <= half_length and abs(local_z) <= half_width
    return inside, (local_x, local_z)

def lerp(start: float, end: float, t: float):
    """
    Linear interpolation between a and b.

    Args:
        a: start value
        b: end value
        t: fraction [0, 1]

    Returns:
        interpolated value
    """

    return start + (end - start) * t

def rotate_around_axis(vec: pg.Vector3, axis: pg.Vector3, angle_rad: float) -> pg.Vector3:
    """Rotate a vector around an axis by a given angle using Rodrigues' rotation formula.
    Axis must be a unit vector.
    Positive angle is clockwise when looking in the direction of the axis vector (right-hand rule)."""

    if not 1 - C.MATH_EPSILON < axis.length_squared() < 1 + C.MATH_EPSILON:
        raise ValueError("Axis must be a unit vector (use .normalize() to normalise it first)")

    cos_a = cos(angle_rad)
    sin_a = sin(angle_rad)
    return (vec * cos_a) + (axis.cross(vec) * sin_a) + (axis * axis.dot(vec) * (1 - cos_a))

def wrap_text(text: str, width: RealNumber, font_family: pg.font.Font) -> list[str]:
    """Wrap text such that when it is displayed, each line is no longer than
    width pixels, in accordance to the given font size and font family."""

    words: list[str] = text.split()

    lines: list[str] = []
    current_line = ""

    for word in words:
        if not current_line:
            current_line = word
            continue

        candidate = f"{current_line} {word}"
        if font_family.size(candidate)[0] <= width:
            current_line = candidate
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines
