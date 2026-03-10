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
from pylines.core.utils import draw_transparent_rect, draw_text, wrap_text, clamp_surf_to_non_empty
from pylines.core.asset_manager_helpers import FLine
from pylines.core.scroll_physics import ScrollPhysics1D

if TYPE_CHECKING:
    from pylines.game.game import Game

class HelpScreen(PopupMenu):
    CONTENT_RECT = pg.Rect(80, 224, 1000, 500)  # left, top, w, h

    def __init__(self, game: Game) -> None:
        super().__init__(game)

        self.static_surface = self.populate_static_surface()
        self.scroll_physics = ScrollPhysics1D(self.static_surface.get_height(), self.CONTENT_RECT.height)

    def take_input(self, keys: pg.key.ScancodeWrapper, events: list[pg.event.Event], dt_ms: int):
        self.scroll_physics.take_input(keys, events, dt_ms)

    def update(self, dt_ms: int) -> None:
        self.scroll_physics.update(dt_ms)

    def populate_static_surface(self) -> Surface:
        """Create the static text surface to avoid expensive
        per-frame text draws"""

        top = 0
        left = 0
        width = C.WN_W - 320
        indent_px = 24

        logical_y = top

        # Make new surface with dummy large height
        surf = pg.Surface((self.CONTENT_RECT.width, 5000), pg.SRCALPHA)

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
                    render_y = logical_y
                    if i == 0:
                        draw_text(surf, (x, render_y), 'left', 'top', bullet_prefix, colour, size, font)
                    draw_text(surf, (x + prefix_w, render_y), 'left', 'top', line, colour, size, font)
                    logical_y += font.get_linesize() + 4
            else:
                for line in wrap_text(fline.text, max_w, font):
                    render_y = logical_y
                    draw_text(surf, (x, render_y), 'left', 'top', line, colour, size, font)
                    logical_y += font.get_linesize() + 4

            logical_y += 6  # extra spacing between FLine entries

        surf = clamp_surf_to_non_empty(surf)

        return surf

    def draw(self, surface: Surface) -> None:
        # Background overlay
        draw_transparent_rect(
            surface, (30, 30), (C.WN_W - 60, C.WN_H - 60), border_thickness=3
        )

        # Logo / title
        rect = self.game.assets.images.logo.get_rect(center=(C.WN_W//2, 100))
        surface.blit(self.game.assets.images.logo, rect)
        draw_text(
            surface, (rect.centerx, rect.bottom + 8), 'centre', 'top',
            "Help", (0, 192, 255), 36, self.game.assets.fonts.monospaced
        )

        subsurface = self.static_surface.subsurface((0, self.scroll_physics.disp, self.CONTENT_RECT.width, self.scroll_physics.view_height))
        surface.blit(subsurface, (80, rect.bottom + 80))

        # Scrollbar
        width = self.CONTENT_RECT.width

        scrollbar_w = 12
        scrollbar_x = self.CONTENT_RECT.left + width + 20

        content_height = self.scroll_physics.max_disp
        view_height = max(0, self.CONTENT_RECT.bottom - self.CONTENT_RECT.top)

        scrollbar_h = max(0, self.CONTENT_RECT.bottom - self.CONTENT_RECT.top)
        bar_bg = pg.Rect(scrollbar_x, self.CONTENT_RECT.top, scrollbar_w, scrollbar_h)
        pg.draw.rect(surface, (55, 55, 55), bar_bg)

        if content_height > 0:
            if self.scroll_physics.max_disp == 0:
                thumb_h = scrollbar_h
                thumb_y = self.CONTENT_RECT.top
            else:
                thumb_h = max(24, int(scrollbar_h * (view_height / content_height)))
                max_thumb_y = self.CONTENT_RECT.top + scrollbar_h - thumb_h
                thumb_y = self.CONTENT_RECT.top + int((self.scroll_physics.disp / self.scroll_physics.max_disp) * (max_thumb_y - self.CONTENT_RECT.top))

            thumb = pg.Rect(scrollbar_x, thumb_y, scrollbar_w, thumb_h)
            pg.draw.rect(surface, (185, 185, 185), thumb)