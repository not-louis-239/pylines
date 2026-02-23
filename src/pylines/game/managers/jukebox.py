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

import pylines.core.colours as cols
import pylines.core.constants as C
from pylines.core.audio_manager import SFXChannelID
from pylines.core.asset_manager_helpers import ControlsSectionID, MusicID
from pylines.core.custom_types import Sound, Surface
from pylines.core.utils import draw_text, draw_transparent_rect
from pylines.game.managers.pop_up_menus import PopupMenu

if TYPE_CHECKING:
    from pylines.game.game import Game

class Jukebox(PopupMenu):
    """Dedicated class for managing music."""

    VOLUME_INCREMENT = 0.1  # amount by which to change volume when pressing volume buttons

    def __init__(self, game: Game, tracks: dict[MusicID, Sound]) -> None:
        super().__init__(game)

        if not tracks:
            raise ValueError("Jukebox needs at least one track")

        self.tracks = tracks
        self.current_idx = 0
        self.volume: float = 0

        self.surface: Surface = Surface((540, 600), flags=pg.SRCALPHA)

    def get_current_track(self) -> Sound:
        track_list = list(self.tracks.values())
        return track_list[self.current_idx]

    def prev_track(self) -> None:
        if not self.tracks:
            raise ValueError("This jukebox has no tracks")

        self.current_idx = (self.current_idx - 1) % len(self.tracks)

    def next_track(self) -> None:
        if not self.tracks:
            raise ValueError("This jukebox has no tracks")

        self.current_idx = (self.current_idx + 1) % len(self.tracks)

    def draw(self, surface: Surface) -> None:
        # Clear jukebox menu surface
        self.surface.fill((0, 0, 0, 0))
        draw_transparent_rect(self.surface, (0, 0), (540, 600), (0, 0, 0, 150), 2)

        # Title
        draw_text(
            self.surface, (270, 48), 'centre', 'centre',
            "Jukebox", cols.WHITE, 35, self.game.assets.fonts.monospaced
        )

        # Show jukebox controls
        for i, (key, desc) in enumerate(self.game.assets.texts.controls_sections[ControlsSectionID.JUKEBOX].keys.items()):
            draw_text(
                self.surface, (16, 105 + 25 * i), 'left', 'centre',
                key, cols.BLUE, 20, self.game.assets.fonts.monospaced
            )
            draw_text(
                self.surface, (96, 105 + 25 * i), 'left', 'centre',
                desc, cols.WHITE, 20, self.game.assets.fonts.monospaced
            )

        # Volume display
        volume_display_centre_y = 190

        draw_text(
            self.surface, (16, volume_display_centre_y), 'left', 'centre',
            "Volume:", cols.WHITE, 20, self.game.assets.fonts.monospaced
        )

        # Volume bar
        bar_rect = pg.Rect(96, volume_display_centre_y - 6, 380, 12)
        buffer_width = 3
        pg.draw.rect(self.surface, cols.WHITE, bar_rect, width=1)

        inner_bar_width = (380 - 2 * buffer_width) * self.volume
        inner_bar_rect = pg.Rect(96 + buffer_width, volume_display_centre_y - 6 + buffer_width, inner_bar_width, 12 - 2 * buffer_width)
        pg.draw.rect(self.surface, cols.WHITE, inner_bar_rect)

        # Blit entire display onto target surface
        blit_y = C.WN_H - (C.WN_H * 0.93) * self.state.animation_open
        surface.blit(self.surface, (C.WN_W/2 - 270, blit_y))
