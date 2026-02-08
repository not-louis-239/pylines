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

from typing import TYPE_CHECKING, cast

import pygame as pg
from OpenGL import GL as gl, GLU as glu

import pylines.core.constants as C
from pylines.core.custom_types import EventList, ScancodeWrapper
from pylines.game.states import State, StateID
from pylines.core.utils import draw_text, clamp
from pylines.core.custom_types import Surface

if TYPE_CHECKING:
    from pylines.game.game import Game

class CreditsScreen(State):
    BASE_SCROLL_SPEED = 60  # px/s

    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.display_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
        self.texture_id = gl.glGenTextures(1)

        self.scroll_offset = 0
        self.offset_vel = CreditsScreen.BASE_SCROLL_SPEED

        self.credits_surface = self._populate_credits_surface()

    def _populate_credits_surface(self) -> Surface:
        """Draw credits text to a surface once. This avoids wasting
        resources drawing text every frame."""

        surf = pg.Surface((C.WN_W, C.WN_H * 5))

        ...  # TODO: render credits

        return surf

    def reset(self) -> None:
        self.scroll_offset = 0

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        if keys[pg.K_ESCAPE]:
            self.game.enter_state(StateID.TITLE)

        direction = 0

        if keys[pg.K_UP]:
            direction -= 1
        if keys[pg.K_DOWN]:
            direction += 1

        speed = CreditsScreen.BASE_SCROLL_SPEED * (3 if keys[pg.K_SPACE] else 1)
        self.offset_vel = (direction if direction != 0 else 1) * speed

    def update(self, dt: int) -> None:
        self.scroll_offset += self.offset_vel * dt/1000

    def draw(self, wn: pg.Surface):
        # Fill the display surface
        self.display_surface.fill((0, 0, 0))

        height = self.credits_surface.get_height()
        assert height > C.WN_H, "Credits surface height must be greater than window height to avoid subsurface errors."
        visible_rect = pg.Rect(0, clamp(self.scroll_offset, (0, height - C.WN_H)), C.WN_W, C.WN_H)  # clamp avoids ValueError
        self.display_surface.blit(self.credits_surface.subsurface(visible_rect), (0, 0))

        draw_text(
            self.display_surface, (20, 30), 'left', 'centre',
            "Press Esc to exit", (110, 110, 110), 30, self.fonts.monospaced
        )

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
