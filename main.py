#!/usr/bin/env python3

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

import os
import sys

import pygame as pg
from OpenGL import GL as gl, GLU as glu

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from pylines.core.constants import (
    FPS,
    INNER_RENDER_LIMIT,
    OUTER_RENDER_LIMIT,
    TPS,
    WN_H,
    WN_W,
)
from pylines.game.game import Game


def main():
    pg.init()

    TICK = pg.USEREVENT + 1
    clock = pg.time.Clock()
    pg.time.set_timer(TICK, int(1000/TPS))

    wn = pg.display.set_mode((WN_W, WN_H), pg.DOUBLEBUF | pg.OPENGL)
    pg.display.set_caption("Pylines")
    pg.mixer.set_num_channels(32)

    # Initialize OpenGL
    gl.glViewport(0, 0, WN_W, WN_H)
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    glu.gluPerspective(45, WN_W/WN_H, INNER_RENDER_LIMIT, OUTER_RENDER_LIMIT)  # Field of view, aspect ratio, near, far clipping plane
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()
    gl.glEnable(gl.GL_DEPTH_TEST)  # Enable depth testing for 3D objects

    game = Game()

    running = True
    while running:
        events = pg.event.get()
        for event in events:
            # Quit
            if event.type == pg.QUIT:
                game.quit_game()
                running = False

            if event.type == TICK:
                game.update(1000/TPS)

        dt = clock.tick(FPS)
        keys = pg.key.get_pressed()

        game.take_input(keys, events, dt)
        game.draw(wn)
        pg.display.flip()

    pg.quit()

if __name__ == "__main__":
    main()
