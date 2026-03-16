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

import sys

try:
    import os

    import time
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
    from pylines.core.resolution_manager import ViewportManager
    from pylines.game.game import Game
    from pylines.game.managers.diagnostics import TimeInterval
except KeyboardInterrupt:
    print("\nKeyboardInterrupt received during import time. Exiting.")
    sys.exit(0)

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
        windowed_size = (WN_W, WN_H)
        windowed_flags = pg.DOUBLEBUF | pg.OPENGL | pg.RESIZABLE
        fullscreen_flags = pg.DOUBLEBUF | pg.OPENGL | pg.FULLSCREEN
        supports_auto_resize = pg.version.vernum >= (2, 0, 0)

        viewport_manager = ViewportManager(
            initial_windowed_size=windowed_size,
            windowed_flags=windowed_flags,
            fullscreen_flags=fullscreen_flags,
            supports_auto_resize=supports_auto_resize,
            fov=FOV,
            inner_render_limit=INNER_RENDER_LIMIT,
            outer_render_limit=OUTER_RENDER_LIMIT,
        )

        wn = viewport_manager.create_window()
        pg.display.set_caption("Pylines")
        pg.mixer.set_num_channels(32)

        # Initialize OpenGL
        viewport_manager.update_gl_viewport(windowed_size)
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
                    continue

                if event.type == pg.KEYDOWN:
                    mod = event.mod
                    cmd_mod = pg.KMOD_META | pg.KMOD_GUI
                    if event.key == pg.K_F11 or (
                        event.key == pg.K_f and (mod & pg.KMOD_CTRL) and (mod & cmd_mod)
                    ):
                        wn = viewport_manager.toggle_fullscreen(wn)

                window_resized = []
                if hasattr(pg, "WINDOWRESIZED"):
                    window_resized.append(pg.WINDOWRESIZED)
                if hasattr(pg, "WINDOWSIZECHANGED"):
                    window_resized.append(pg.WINDOWSIZECHANGED)
                wn = viewport_manager.handle_window_resize_event(
                    wn,
                    event, window_resized,
                )

            keys = pg.key.get_pressed()

            game.take_input(keys, events, dt_ms)

            while time_accum > fixed_dt_ms:
                ti = time.perf_counter()
                game.update(fixed_dt_ms)
                tf = time.perf_counter()

                game.diagnostics_manager.record_tick(TimeInterval(ti, tf))

                time_accum -= fixed_dt_ms

            ti = time.perf_counter()
            game.draw(wn)
            pg.display.flip()
            tf = time.perf_counter()

            game.diagnostics_manager.record_frame(TimeInterval(ti, tf))

    except KeyboardInterrupt:
        if game is not None:
            game.quit()  # cleanup + save data to disk

        print("\nKeyboardInterrupt received. Exiting.")

    finally:
        pg.quit()

if __name__ == "__main__":
    main()
