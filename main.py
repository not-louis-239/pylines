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
from OpenGL import GL as gl
from OpenGL import GLU as glu

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from pylines.core.constants import (
    FPS,
    INNER_RENDER_LIMIT,
    OUTER_RENDER_LIMIT,
    TPS,
    WN_H,
    WN_W,
    FOV
)
from pylines.game.game import Game


def main():
    game = None

    try:
        # Initialise Pygame and clock
        pg.init()

        # Initialise time instruments
        clock = pg.time.Clock()
        fixed_dt_ms = 1000 / TPS
        time_accum: float = 0  # stores time since last batch of updates

        # Initialise window and mixer
        wn = pg.display.set_mode((WN_W, WN_H), pg.DOUBLEBUF | pg.OPENGL)
        pg.display.set_caption("Pylines")
        pg.mixer.set_num_channels(32)

        # Initialize OpenGL
        gl.glViewport(0, 0, WN_W, WN_H)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(FOV, WN_W/WN_H, INNER_RENDER_LIMIT, OUTER_RENDER_LIMIT)  # Field of view, aspect ratio, near, far clipping plane
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glEnable(gl.GL_DEPTH_TEST)  # Enable depth testing for 3D objects

        # Create Game instance
        game = Game()

        # Main loop
        running = True
        while running:
            dt_ms = clock.tick(FPS)
            time_accum += dt_ms

            events = pg.event.get()

            for event in events:
                if event.type == pg.QUIT:
                    game.quit()
                    running = False

            keys = pg.key.get_pressed()

            game.take_input(keys, events, dt_ms)

            while time_accum > fixed_dt_ms:
                game.update(fixed_dt_ms)
                time_accum -= fixed_dt_ms

            game.draw(wn)
            pg.display.flip()

    except KeyboardInterrupt:
        if game is not None:
            game.quit()  # cleanup + save data to disk

        print("\nKeyboardInterrupt received. Exiting.")

    finally:
        pg.quit()

if __name__ == "__main__":
    main()
