import sys
import os
import OpenGL.GL as gl
import OpenGL.GLU as glu
import pygame as pg

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from pylines.core.constants import (FPS, INNER_RENDER_LIMIT, OUTER_RENDER_LIMIT, TPS,
                            WN_H, WN_W)
from pylines.game.game import Game


def main():
    pg.init()

    TICK = pg.USEREVENT + 1
    clock = pg.time.Clock()
    pg.time.set_timer(TICK, int(1000/TPS))

    wn = pg.display.set_mode((WN_W, WN_H), pg.DOUBLEBUF | pg.OPENGL)
    pg.display.set_caption("Pylines")

    # Initialize OpenGL
    gl.glViewport(0, 0, WN_W, WN_H)
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    glu.gluPerspective(45, WN_W/WN_H, INNER_RENDER_LIMIT, OUTER_RENDER_LIMIT) # Field of view, aspect ratio, near, far clipping plane
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()
    gl.glEnable(gl.GL_DEPTH_TEST) # Enable depth testing for 3D objects

    game = Game()

    running = True
    while running:
        for event in pg.event.get():
            # Quit
            if event.type == pg.QUIT:
                running = False

            if event.type == TICK:
                game.update(1000/TPS)

        dt = clock.tick(FPS)
        keys = pg.key.get_pressed()

        game.take_input(keys, dt)
        game.draw(wn)
        pg.display.flip()

    pg.quit()

if __name__ == "__main__":
    main()
