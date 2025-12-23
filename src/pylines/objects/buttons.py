from pathlib import Path

import pygame as pg

from pylines.core.custom_types import Colour, Coord2, Surface
from pylines.core.utils import draw_text

class Button:
    def __init__(self, pos: Coord2, w, h,
                 colour: Colour, text_colour: Colour, text: str, font: Path) -> None:
        self.pos = pg.Vector2(*pos)
        self.w = w
        self.h = h
        self.colour = colour
        self.text_colour = text_colour
        self.text = text
        self.font = font

        self.rect = pg.Rect(0, 0, self.w, self.h)
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    # Returns True once when held
    def check_click(self, event_list: list[pg.event.Event]) -> bool:
        for e in event_list:
            if e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                if self.rect.collidepoint(e.pos):
                    return True
        return False

    def draw(self, wn: Surface):
        pg.draw.rect(wn, self.colour, self.rect)
        draw_text(wn, (int(self.pos.x), int(self.pos.y)), 'centre', 'centre', self.text, self.text_colour, 30, self.font)
