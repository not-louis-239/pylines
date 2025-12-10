from typing import Generator
import pygame as pg
from pygame.surface import Surface
from core.custom_types import Colour

def draw_text(surface: Surface, pos: tuple[int, int], horiz_align: str, vert_align: str,
              text: str, colour: Colour, size: int, font_family: str | None = None):
    font = pg.font.SysFont(font_family, size) if font_family else pg.font.SysFont(None, size)
    img = font.render(text, True, colour)
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
