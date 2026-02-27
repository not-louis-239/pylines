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

import pylines.core.colours as cols
import pylines.core.constants as C
from pylines.core.asset_manager_helpers import ControlsSectionID
from pylines.core.custom_types import Surface
from pylines.core.utils import draw_text

from .pop_up_menus import PopupMenu

if TYPE_CHECKING:
    from pylines.game.game import Game

class ControlsReference(PopupMenu):
    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.surface = self.generate_surface()

    def generate_surface(self) -> Surface:
        """Draw everything to a cached surface for the controls mini-reference
        to avoid wasting resources drawing it each frame while active."""

        surf = pg.Surface((400, 600), flags=pg.SRCALPHA)

        surf.fill((0, 0, 0, 180))
        pg.draw.rect(surf, cols.WHITE, surf.get_rect(), 2)  # 2px-wide white border

        title_y = 30
        draw_text(surf, (35, title_y), 'left', 'centre', "Controls (Quick Ref)", cols.WHITE, 24, self.game.assets.fonts.monospaced)

        def draw_section(title: str, start_y: int, items: dict[str, str]) -> int:
            """Draw a section and return a position y-value for the next section."""

            draw_text(surf, (35, start_y), 'left', 'centre', title, (0, 192, 255), 20, self.game.assets.fonts.monospaced)
            y = start_y + 35
            for key, desc in items.items():
                draw_text(surf, (35, y), 'left', 'centre', key, (150, 230, 255), 16, self.game.assets.fonts.monospaced)
                draw_text(surf, (110, y), 'left', 'centre', desc, cols.WHITE, 16, self.game.assets.fonts.monospaced)
                y += 20
            return y

        y = 75
        y = draw_section(
            "Main Controls", y,
            self.game.assets.texts.controls_sections[ControlsSectionID.MAIN].keys
        )

        y += 10
        y = draw_section(
            "Displays", y,
            self.game.assets.texts.controls_sections[ControlsSectionID.DISPLAYS].keys,
        )

        y += 10
        y = draw_section(
            "While Map Open", y,
            self.game.assets.texts.controls_sections[ControlsSectionID.MAP].keys,
        )

        y += 10
        y = draw_section(
            "Utilities", y,
            self.game.assets.texts.controls_sections[ControlsSectionID.UTILITIES].keys,
        )

        draw_text(surf, (200, 575), 'centre', 'centre', "Press O to close", (150, 230, 255), 18, self.game.assets.fonts.monospaced)

        return surf

    def draw(self, surface: Surface) -> None:
        w, _ = self.surface.get_size()
        surface.blit(self.surface, (int(C.WN_W - (w + 30) * self.state.animation_open), 50))  # centred when fully active