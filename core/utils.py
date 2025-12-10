import pygame as pg
from pygame.surface import Surface
from core.constants import Colour

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
