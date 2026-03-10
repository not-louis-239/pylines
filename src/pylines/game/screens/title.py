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

import pylines.core.colours as cols
import pylines.core.constants as C
from pylines.core.asset_manager import FLine
from pylines.core.asset_manager_helpers import ControlsSection, ControlsSectionID
from pylines.core.custom_types import Colour, EventList, ScancodeWrapper, Surface
from pylines.core.utils import draw_text, draw_transparent_rect, wrap_text
from pylines.game.states import State, StateID
from pylines.objects.buttons import Button, ImageButton
from pylines.game.managers.help_screen_renderer import HelpScreen

if TYPE_CHECKING:
    from pylines.game.game import Game

class TitleScreen(State):
    def __init__(self, game: Game):
        super().__init__(game)
        self.display_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
        self.texture_id = gl.glGenTextures(1)

        self.settings_button = Button(
            (90, C.WN_H-50), 150, 60, (25, 75, 75), (200, 255, 255),
            "Settings", self.fonts.monospaced, 30
        )

        self.credits_button = Button(
            (250, C.WN_H-50), 150, 60, (25, 75, 75), (200, 255, 255),
            "Credits", self.fonts.monospaced, 30
        )

        self.return_button = Button(
            (C.WN_W - 120, C.WN_H - 60), 200, 60, (25, 75, 75), (200, 255, 255),
            "Return", self.fonts.monospaced, 30
        )

        self.help_screen = HelpScreen(self.game)
        self.help_button = ImageButton((C.WN_W - 75, C.WN_H - 75), self.images.help_icon)

    def reset(self) -> None:
        self.sounds.stall_warning.stop()

    def update(self, dt: int) -> None:
        self.game.menu_image_manager.update(dt)

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        if self.pressed(keys, pg.K_SPACE) and not self.help_screen.state.visible:
            self.game.enter_state(StateID.BRIEFING if self.game.save_data.show_briefing else StateID.GAME)
        if self.settings_button.check_click(events) and not self.help_screen.state.visible:
            self.game.enter_state(StateID.SETTINGS)
        if self.credits_button.check_click(events) and not self.help_screen.state.visible:
            self.game.enter_state(StateID.CREDITS)

        if self.help_button.check_click(events) and not self.help_screen.state.visible:
            self.help_screen.state.visible = True
        elif self.return_button.check_click(events) and self.help_screen.state.visible:
            self.help_screen.state.visible = False

        if self.help_screen.state.visible:
            self.help_screen.take_input(keys, events, dt)

        self.update_prev_keys(keys)

    def draw_title_screen(self):
        rect = self.images.logo.get_rect(center=(C.WN_W//2, C.WN_H*0.11))
        self.display_surface.blit(self.images.logo, rect)

        draw_transparent_rect(
            self.display_surface, (C.WN_W // 2 - C.WN_W * 0.4, C.WN_H // 2 - C.WN_H * 0.28), (C.WN_W * 0.8, C.WN_H * 0.54),
            (0, 0, 0, 85), 3
        )

        text = "Press Space for briefing" if self.game.save_data.show_briefing else "Press Space to fly"
        draw_text(self.display_surface, (C.WN_W//2, C.WN_H*0.85), 'centre', 'centre', text, (255, 255, 255), 30, self.fonts.monospaced)

        draw_text(self.display_surface, (C.WN_W//2, 0.97*C.WN_H), 'centre', 'centre', "Copyright (C) 2025-2026 Louis Masarei-Boulton.", (127, 127, 127), 15, self.fonts.monospaced)

        controls_sections: dict[ControlsSectionID, ControlsSection] = self.game.assets.texts.controls_sections  # Local alias
        draw_text(self.display_surface, (C.WN_W//2 - 480, C.WN_H*0.3), 'left', 'centre', "Read Before Flight", (0, 192, 255), 40, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.MAIN].keys.items()):
            draw_text(self.display_surface, (C.WN_W//2 - 480, C.WN_H * (0.38 + 0.04*i)), 'left', 'centre', key, (150, 230, 255), 27, self.fonts.monospaced)
            draw_text(self.display_surface, (C.WN_W//2 - 360, C.WN_H * (0.38 + 0.04*i)), 'left', 'centre', action, cols.WHITE, 27, self.fonts.monospaced)

        draw_text(self.display_surface, (C.WN_W//2 + 20, C.WN_H*0.26), 'left', 'centre', ControlsSectionID.DISPLAYS, (0, 192, 255), 25, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.DISPLAYS].keys.items()):
            draw_text(self.display_surface, (C.WN_W//2 + 20, C.WN_H * (0.31 + 0.03*i)), 'left', 'centre', key, (150, 230, 255), 21, self.fonts.monospaced)
            draw_text(self.display_surface, (C.WN_W//2 + 140, C.WN_H * (0.31 + 0.03*i)), 'left', 'centre', action, cols.WHITE, 21, self.fonts.monospaced)

        draw_text(self.display_surface, (C.WN_W//2 + 20, C.WN_H*0.4), 'left', 'centre', ControlsSectionID.MAP, (0, 192, 255), 25, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.MAP].keys.items()):
            draw_text(self.display_surface, (C.WN_W//2 + 20, C.WN_H * (0.45 + 0.03*i)), 'left', 'centre', key, (150, 230, 255), 21, self.fonts.monospaced)
            draw_text(self.display_surface, (C.WN_W//2 + 140, C.WN_H * (0.45 + 0.03*i)), 'left', 'centre', action, cols.WHITE, 21, self.fonts.monospaced)
        note = controls_sections[ControlsSectionID.MAP].note
        assert note is not None
        draw_text(self.display_surface, (C.WN_W//2 + 20, C.WN_H * (0.45 + 0.03 * (len(controls_sections[ControlsSectionID.MAP].keys) + 0.5))), 'left', 'centre', note, (255, 255, 255), 21, self.fonts.monospaced)

        draw_text(self.display_surface, (C.WN_W//2 + 20, C.WN_H*0.64), 'left', 'centre', ControlsSectionID.UTILITIES, (0, 192, 255), 25, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.UTILITIES].keys.items()):
            draw_text(self.display_surface, (C.WN_W//2 + 20, C.WN_H * (0.69 + 0.03*i)), 'left', 'centre', key, (150, 230, 255), 21, self.fonts.monospaced)
            draw_text(self.display_surface, (C.WN_W//2 + 140, C.WN_H * (0.69 + 0.03*i)), 'left', 'centre', action, cols.WHITE, 21, self.fonts.monospaced)

        self.settings_button.draw(self.display_surface)
        self.credits_button.draw(self.display_surface)
        self.help_button.draw(self.display_surface)

    def draw(self, wn: Surface):
        # Clear the display surface first
        self.display_surface.fill((0, 0, 0))

        self.game.menu_image_manager.draw_current(self.display_surface)

        if self.help_screen.state.visible:
            self.help_screen.draw(self.display_surface)
        else:
            self.draw_title_screen()

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
