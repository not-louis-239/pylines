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

from pathlib import Path

import pygame as pg

from pylines.core.custom_types import Colour, Coord2, Surface, RealNumber, EventList
from pylines.core.utils import draw_text

class Button:
    def __init__(self, pos: Coord2, w: RealNumber, h: RealNumber,
                 colour: Colour, text_colour: Colour, text: str, font: Path, font_size: int) -> None:
        self.pos = pg.Vector2(*pos)
        self.w = w
        self.h = h
        self.colour = colour
        self.text_colour = text_colour
        self.text = text
        self.font = font
        self.font_size = font_size

        self.rect = pg.Rect(0, 0, self.w, self.h)
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    # Returns True once when held
    def check_click(self, event_list: EventList) -> bool:
        for e in event_list:
            if e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                if self.rect.collidepoint(e.pos):
                    return True
        return False

    def draw(self, wn: Surface):
        pg.draw.rect(wn, self.colour, self.rect)
        draw_text(wn, (int(self.pos.x), int(self.pos.y)), 'centre', 'centre', self.text, self.text_colour, 30, self.font)
