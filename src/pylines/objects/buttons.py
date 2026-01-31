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

from pylines.core.custom_types import Colour, Coord2, EventList, RealNumber, Surface
from pylines.core.utils import draw_text


class Button:
    def __init__(
        self, pos: Coord2, w: RealNumber, h: RealNumber,
        colour: Colour, text_colour: Colour, text: str, font: Path, font_size: int,
    ) -> None:
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

    def check_click(self, event_list: EventList) -> bool:
        # Returns True once on press
        for event in event_list:
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if self.rect.collidepoint(event.pos):
                    return True
        return False

    def draw(self, wn: Surface):
        pg.draw.rect(wn, self.colour, self.rect)
        draw_text(wn, (int(self.pos.x), int(self.pos.y)), 'centre', 'centre', self.text, self.text_colour, 30, self.font)

class ImageButton(Button):
    def __init__(
        self, pos: Coord2, image: Surface
    ) -> None:
        self.pos = pg.Vector2(*pos)
        self.image = image
        self.w, self.h = self.image.get_size()

        self.rect = pg.Rect(0, 0, self.w, self.h)
        self.rect.center = int(self.pos.x), int(self.pos.y)

    # Returns True once on press
    def check_click(self, event_list: EventList) -> bool:
        for event in event_list:
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if self.rect.collidepoint(event.pos):
                    return True
        return False

    def draw(self, wn: Surface):
        wn.blit(self.image, self.rect)

class Checkbox(Button):
    def __init__(
        self, pos: Coord2, w: RealNumber, h: RealNumber,
        colour: Colour, text_colour: Colour, text: str, font: Path, font_size: int,
        checked: bool = False
    ) -> None:
        super().__init__(pos, w, h, colour, text_colour, text, font, font_size)
        self.checked = checked

    def toggle(self):
        self.checked = not self.checked

    def draw(self, wn: Surface):
        # Draw white border
        BORDER_COL: Colour = (255, 255, 255)
        BORDER_WIDTH: RealNumber = 2
        pg.draw.rect(wn, BORDER_COL, self.rect)

        inner_rect = pg.Rect(0, 0, self.w - 2 * BORDER_WIDTH, self.h - 2 * BORDER_WIDTH)
        inner_rect.center = int(self.pos.x), int(self.pos.y)

        # Draw button
        pg.draw.rect(wn, self.colour, inner_rect)

        # Draw a circle in the middle of the box if checked
        if self.checked:
            pg.draw.circle(wn, (255, 255, 255), (self.pos.x, self.pos.y), 5)

        # Draw text like a normal button
        draw_text(
            wn, (int(self.pos.x + self.w//2 + 20), int(self.pos.y)),
            'left', 'centre', self.text,
            self.text_colour, 30, self.font
        )
