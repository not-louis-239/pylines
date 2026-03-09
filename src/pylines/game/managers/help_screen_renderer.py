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

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame as pg

import pylines.core.constants as C
import pylines.core.colours as cols
from pylines.core.custom_types import Surface, Colour
from pylines.game.managers.pop_up_menus import PopupMenu
from pylines.core.utils import draw_transparent_rect, draw_text, wrap_text
from pylines.core.asset_manager_helpers import FLine
from pylines.core.scroll_physics import ScrollPhysics

if TYPE_CHECKING:
    from pylines.game.game import Game

class HelpScreen(PopupMenu):
    def __init__(self, game: Game) -> None:
        super().__init__(game)

        self.static_surface = self.populate_static_surface()
        self.scroll_physics = ScrollPhysics(self.static_surface.get_height(), 400)

    def take_input(self, dt_ms: int, keys: pg.key.ScancodeWrapper, events: list[pg.event.Event]):
        self.scroll_physics.take_input(dt_ms, keys, events)

    def update(self, dt_ms: int) -> None:
        self.scroll_physics.update(dt_ms)

    def populate_static_surface(self) -> Surface:
        # TODO: move static elements to this function

        surf = pg.Surface((C.WN_W, 5000), pg.SRCALPHA)

        rect = self.game.assets.images.logo.get_rect(center=(C.WN_W//2, 100))
        indent_px = 24
        left = 80
        top = rect.bottom + 80
        bottom = C.WN_H - 120
        width = C.WN_W - 320

        # Fill the surf with text
        visual_styles: dict[FLine.Style, tuple[int, Colour, bool]] = {
            FLine.Style.HEADING_1: (36, (0, 192, 255), False),
            FLine.Style.HEADING_2: (28, (0, 192, 255), False),
            FLine.Style.BULLET: (24, cols.WHITE, True),
            FLine.Style.NORMAL: (24, cols.WHITE, False),
        }

        for fline in self.game.assets.texts.help_lines:
            size, colour, bullet = visual_styles[fline.style]

            x = left + indent_px * fline.indent
            max_w = width - indent_px * fline.indent

            font = pg.font.Font(self.game.assets.fonts.monospaced, size)
            if bullet:
                bullet_prefix = "• "
                prefix_w = font.size(bullet_prefix)[0]
                wrapped = wrap_text(fline.text, max_w - prefix_w, font)
                for i, line in enumerate(wrapped):
                    render_y = logical_y - self.scroll_disp
                    if render_y + font.get_linesize() >= top and render_y <= bottom:
                        if i == 0:
                            draw_text(surf, (x, render_y), 'left', 'top', bullet_prefix, colour, size, font)
                        draw_text(surf, (x + prefix_w, render_y), 'left', 'top', line, colour, size, font)
                    logical_y += font.get_linesize() + 4
            else:
                for line in wrap_text(fline.text, max_w, font):
                    render_y = logical_y - self.scroll_disp
                    if render_y + font.get_linesize() >= top and render_y <= bottom:
                        draw_text(surf, (x, render_y), 'left', 'top', line, colour, size, font)
                    logical_y += font.get_linesize() + 4

            logical_y += 6  # extra spacing between FLine entries

        # TODO: Clamp the surf to only non-empty regions (cut off all transparent whitespace at the edges, if any)

        return surf

    def draw(self, surface: Surface) -> None:
        draw_transparent_rect(
            surface, (30, 30), (C.WN_W - 60, C.WN_H - 60), border_thickness=3
        )

        rect = self.game.assets.images.logo.get_rect(center=(C.WN_W//2, 100))
        surface.blit(self.game.assets.images.logo, rect)
        draw_text(
            surface, (rect.centerx, rect.bottom + 8), 'centre', 'top',
            "Help", (0, 192, 255), 36, self.game.assets.fonts.monospaced
        )

        left = 80
        top = rect.bottom + 80
        bottom = C.WN_H - 120
        width = C.WN_W - 320

        logical_y = top
        scrollbar_w = 12
        scrollbar_x = left + width + 20

        content_height = max(0, logical_y - top)
        view_height = max(0, bottom - top)
        self.help_max_offset = max(0, content_height - view_height)
        self.scroll_disp = max(0, min(self.scroll_disp, self.help_max_offset))

        scrollbar_h = max(0, bottom - top)
        bar_bg = pg.Rect(scrollbar_x, top, scrollbar_w, scrollbar_h)
        pg.draw.rect(surface, (55, 55, 55), bar_bg)

        if content_height > 0:
            if self.help_max_offset == 0:
                thumb_h = scrollbar_h
                thumb_y = top
            else:
                thumb_h = max(24, int(scrollbar_h * (view_height / content_height)))
                max_thumb_y = top + scrollbar_h - thumb_h
                thumb_y = top + int((self.scroll_disp / self.help_max_offset) * (max_thumb_y - top))

            thumb = pg.Rect(scrollbar_x, thumb_y, scrollbar_w, thumb_h)
            pg.draw.rect(surface, (185, 185, 185), thumb)