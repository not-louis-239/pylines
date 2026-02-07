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
from OpenGL import GL as gl
from OpenGL import GLU as glu

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
        self.progress: float = 0.0
        self.display_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
        self.texture_id = gl.glGenTextures(1)
        self.gen = self._load_game()
        self.current_msg: str = "Loading..."

    def _load_game(self):
        # Between each chunk of work:
        #    yield (before work) - present last frame
        #    yield (after work)  - present result

        # Initial yield so first frame has a chance to draw
        yield

        # Environment
        yield
        world_data = self.game.assets.world
        self.game.env = Environment(
            world_data,
            self.game.assets.fonts,
            self.game.assets.images,
            diagonal_split='AD'
        )
        self.progress = 0.2
        self.current_msg = "Setting up the world"
        yield

        # Make heavier states
        yield
        new_screen = GameScreen(self.game)
        self.game.states[StateID.GAME] = new_screen
        self.progress = 0.3
        self.current_msg = "Initialising simulation core"
        yield

        for prog, msg in new_screen._build():
            yield
            self.progress = prog
            self.current_msg = msg
            yield

    def reset(self) -> None:
        pass

    def update(self, dt) -> None:
        pass

    def _step(self) -> None:
        try:
            next(self.gen)
        except StopIteration:
            self.game.enter_state(StateID.TITLE)
            return

    def draw(self, wn) -> None:
        self.display_surface.fill((0, 0, 0))
        draw_text(
            self.display_surface, (C.WN_W/2, C.WN_H/2 - 100), 'centre', 'centre',
            "Loading...", (255, 255, 255), 50, self.fonts.monospaced
        )

        draw_text(
            self.display_surface, (C.WN_W/2, C.WN_H/2 + 45), 'centre', 'centre',
            self.current_msg, (255, 255, 255), 30, self.fonts.monospaced
        )

        bar_centre = (C.WN_W // 2, C.WN_H // 2 + 100)

        bar_dims = (400, 30)
        bar_rect = pg.Rect(0, 0, *bar_dims)
        bar_rect.center = bar_centre
        pg.draw.rect(self.display_surface, (255, 255, 255), bar_rect, border_radius=4)

        inner_dims = (bar_dims[0] - 4, bar_dims[1] - 4)
        inner_rect = pg.Rect(0, 0, *inner_dims)
        inner_rect.center = bar_centre
        pg.draw.rect(self.display_surface, (0, 0, 0), inner_rect, border_radius=3)

        # Clamp progress defensively
        progress = max(0.0, min(1.0, self.progress))

        fill_width = int(inner_dims[0] * progress)
        if fill_width > 0:
            fill_rect = pg.Rect(
                inner_rect.left,
                inner_rect.top,
                fill_width,
                inner_dims[1]
            )

            if self.progress < 0.5:
                loading_bar_colour = (255, int(255 * self.progress / 0.5), 0)
            else:
                loading_bar_colour = (int(255 - 255 * (self.progress - 0.5) / 0.5), 255, 0)

            pg.draw.rect(self.display_surface, loading_bar_colour, fill_rect, border_radius=3)

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

        # IMPORTANT:
        # Loading MUST advance once per *rendered frame*, not per update tick.
        # If this step is moved to update(), it may run multiple times before
        # a frame is presented, causing the loading screen to never appear.
        # This is intentional. Loading is a render-driven phase, not a normal state.
        self._step()