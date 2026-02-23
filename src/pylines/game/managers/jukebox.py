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

from typing import TYPE_CHECKING

import pygame as pg

from pylines.core.custom_types import Sound, Surface
from pylines.core.asset_manager_helpers import MusicID, ControlsSectionID
from pylines.core.utils import draw_text, draw_transparent_rect
from pylines.game.managers.pop_up_menus import PopupMenu
import pylines.core.constants as C
import pylines.core.colours as cols

if TYPE_CHECKING:
    from pylines.game.game import Game

class Jukebox(PopupMenu):
    """Dedicated class for managing music."""

    def __init__(self, game: Game, tracks: dict[MusicID, Sound]) -> None:
        super().__init__(game)

        self.tracks = tracks
        self.current_idx = 0

        self.surface: Surface = Surface((540, 600), flags=pg.SRCALPHA)

    def draw(self, surface: Surface) -> None:
        # Clear jukebox menu surface
        self.surface.fill((0, 0, 0, 0))
        draw_transparent_rect(self.surface, (0, 0), (540, 600), (0, 0, 0, 150), 2)

        draw_text(
            self.surface, (270, 48), 'centre', 'centre',
            "Jukebox", cols.WHITE, 35, self.game.assets.fonts.monospaced
        )

        for i, (key, desc) in enumerate(self.game.assets.texts.controls_sections[ControlsSectionID.JUKEBOX].keys.items()):
            draw_text(
                self.surface, (16, 95 + 25 * i), 'left', 'centre',
                key, cols.BLUE, 18, self.game.assets.fonts.monospaced
            )
            draw_text(
                self.surface, (96, 95 + 25 * i), 'left', 'centre',
                desc, cols.WHITE, 18, self.game.assets.fonts.monospaced
            )

        ...

        blit_y = C.WN_H - (C.WN_H / 2 + 300) * self.state.animation_openness
        surface.blit(self.surface, (C.WN_W/2 - 270, blit_y))
