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

"""Generic state management module"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pygame as pg
from OpenGL import GL as gl
from OpenGL import GLU as glu

import pylines.core.constants as C
from pylines.core.colours import WHITE
from pylines.core.custom_types import EventList, ScancodeWrapper, Surface
from pylines.core.utils import draw_text
from pylines.game.states import State, StateID
from pylines.objects.buttons import Button, ImageButton

if TYPE_CHECKING:
    from pylines.game.game import Game

class TitleScreen(State):
    def __init__(self, game: Game):
        super().__init__(game)
        self.display_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
        self.texture_id = gl.glGenTextures(1)

        self.settings_button = Button(
            (120, C.WN_H-90), 200, 80, (25, 75, 75), (200, 255, 255),
            "Settings", self.fonts.monospaced, 30
        )
        self.help_button = ImageButton((C.WN_W - 75, C.WN_H - 75), self.images.help_icon)

    def reset(self) -> None:
        self.sounds.stall_warning.stop()

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        if self.pressed(keys, pg.K_SPACE):
            self.game.enter_state(StateID.BRIEFING if self.game.save_data.show_briefing else StateID.GAME)
        if self.settings_button.check_click(events):
            self.game.enter_state(StateID.SETTINGS)

        self.update_prev_keys(keys)

    def draw(self, wn: Surface):
        # Fill the display surface
        self.display_surface.fill((0, 0, 0))
        rect = self.images.logo.get_rect(center=(C.WN_W//2, C.WN_H*0.15
                                                 ))
        self.display_surface.blit(self.images.logo, rect)

        text = "Press Space for briefing" if self.game.save_data.show_briefing else "Press Space to fly"
        draw_text(self.display_surface, (C.WN_W//2, C.WN_H*0.8), 'centre', 'centre', text, (255, 255, 255), 30, self.fonts.monospaced)

        draw_text(self.display_surface, (C.WN_W//2, 0.95*C.WN_H), 'centre', 'centre', "Copyright (C) 2025-2026 Louis Masarei-Boulton.", (127, 127, 127), 15, self.fonts.monospaced)

        draw_text(self.display_surface, (C.WN_W * 0.3, C.WN_H*0.3), 'centre', 'centre', "Read Before Flight", (0, 192, 255), 40, self.fonts.monospaced)

        controls: dict[str, str] = {
            "W/S": "Throttle",
            "Z/X": "Flaps Up/Down",
            "A/D": "Rudder",
            "Arrows": "Pitch/Yaw",
            "B": "Brake",
            "G": "Cycle GPS dest.",
            "Esc": "Pause"
        }

        for i, (key, desc) in enumerate(controls.items()):
            draw_text(self.display_surface, (C.WN_W//2 - 340, C.WN_H * (0.41 + 0.05*i)), 'right', 'centre', key, (150, 230, 255), 27, self.fonts.monospaced)
            draw_text(self.display_surface, (C.WN_W//2 - 300, C.WN_H * (0.41 + 0.05*i)), 'left', 'centre', desc, WHITE, 27, self.fonts.monospaced)

        draw_text(self.display_surface, (C.WN_W * 3/4, C.WN_H*0.3), 'centre', 'centre', "Map Controls", (0, 192, 255), 30, self.fonts.monospaced)

        controls: dict[str, str] = {
            "M": "Show/Hide Map",
        }

        for i, (key, desc) in enumerate(controls.items()):
            draw_text(self.display_surface, (C.WN_W//2 + 230, C.WN_H * (0.38 + 0.05*i)), 'right', 'centre', key, (150, 230, 255), 27, self.fonts.monospaced)
            draw_text(self.display_surface, (C.WN_W//2 + 270, C.WN_H * (0.38 + 0.05*i)), 'left', 'centre', desc, WHITE, 27, self.fonts.monospaced)

        draw_text(self.display_surface, (C.WN_W * 3/4, C.WN_H*0.47), 'centre', 'centre', "While Map Open:", (0, 192, 255), 30, self.fonts.monospaced)

        controls: dict[str, str] = {
            "W/S": "Zoom In/Out",
            "Arrows": "Pan",
            "Space": "Re-centre",
            "H (hold)": "Show advanced info",
        }

        for i, (key, desc) in enumerate(controls.items()):
            draw_text(self.display_surface, (C.WN_W//2 + 230, C.WN_H * (0.55 + 0.05*i)), 'right', 'centre', key, (150, 230, 255), 27, self.fonts.monospaced)
            draw_text(self.display_surface, (C.WN_W//2 + 270, C.WN_H * (0.55 + 0.05*i)), 'left', 'centre', desc, WHITE, 27, self.fonts.monospaced)

        self.settings_button.draw(self.display_surface)
        self.help_button.draw(self.display_surface)

        # Convert the Pygame surface to an OpenGL texture
        texture_data = pg.image.tostring(self.display_surface, 'RGBA', True)

        gl.glClear(cast(int, gl.GL_COLOR_BUFFER_BIT) | cast(int, gl.GL_DEPTH_BUFFER_BIT))
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, C.WN_W, C.WN_H, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, texture_data)

        # Set up the projection and modelview matrices for 2D drawing
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        glu.gluOrtho2D(0, C.WN_W, 0, C.WN_H)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()

        gl.glDisable(gl.GL_DEPTH_TEST)
        # Draw a full-screen quad with the texture
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBegin(gl.GL_QUADS)
        gl.glTexCoord2f(0, 0)
        gl.glVertex2f(0, 0)
        gl.glTexCoord2f(1, 0)
        gl.glVertex2f(C.WN_W, 0)
        gl.glTexCoord2f(1, 1)
        gl.glVertex2f(C.WN_W, C.WN_H)
        gl.glTexCoord2f(0, 1)
        gl.glVertex2f(0, C.WN_H)
        gl.glEnd()
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_DEPTH_TEST)

        # Restore the previous projection and modelview matrices
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPopMatrix()
