import math
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Literal

import pygame as pg
from pygame.surface import Surface

from core.colours import WHITE
from core.custom_types import AColour, Colour, Coord2, RealNumber


@dataclass
class Rotation:
    pitch: int
    yaw: int
    roll: int

def draw_text(surface: Surface, pos: tuple[float, float],
              horiz_align: Literal['left', 'centre', 'right'],
              vert_align: Literal['top', 'centre', 'bottom'],
              text: str, colour: Colour, size: int, font: pg.font.Font | Path | str | None = None):
    if isinstance(font, pg.font.Font):
        font_obj = font
    elif isinstance(font, (str, Path)):
        font_obj = pg.font.Font(str(font), size)
    else:
        font_obj = pg.font.Font(None, size)

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

def clamp(value: RealNumber, lower: RealNumber, upper: RealNumber):
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