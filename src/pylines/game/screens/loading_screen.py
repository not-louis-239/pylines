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

from typing import cast, TYPE_CHECKING

from OpenGL import GL as gl, GLU as glu
import pygame as pg

from pylines.core import constants as C
from pylines.core.utils import draw_text

from pylines.game.environment import Environment
from pylines.game.screens.game_screen import GameScreen
from pylines.game.states import State, StateID

if TYPE_CHECKING:
    from pylines.game.game import Game

class LoadingScreen(State):
    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.progress: float = 0
        self.display_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
        self.texture_id = gl.glGenTextures(1)
        self.gen = self._load_game()

    def _load_game(self):
        # Environment
        world_data = self.game.assets.world
        self.game.env = Environment(
            world_data,
            self.game.assets.fonts,
            self.game.assets.images,
            diagonal_split='AD'
        )

        self.progress = 0.1
        yield

        # Make heavier states
        self.game.states[StateID.GAME] = GameScreen(self.game)
        self.progress = 1.0
        yield

    def reset(self) -> None:
        pass

    def update(self, dt) -> None:
        try:
            next(self.gen)
        except StopIteration:
            self.game.enter_state(StateID.TITLE)

    def draw(self, wn) -> None:
        self.display_surface.fill((0, 0, 0))
        draw_text(
            self.display_surface, (C.WN_W/2, C.WN_H/2), 'centre', 'centre',
            "Loading...", (255, 255, 255), 30, self.fonts.monospaced
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
