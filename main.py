import pygame as pg
import OpenGL.GL as gl
import OpenGL.GLU as glu

from core.constants import (
    FPS, TPS, WN_H, WN_W,
    INNER_RENDER_LIMIT, OUTER_RENDER_LIMIT
)
from game.game import Game

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
                game.update()

        dt = clock.tick(FPS)
        keys = pg.key.get_pressed()

        game.take_input(keys, dt)
        game.draw(wn)
        pg.display.flip()

    pg.quit()

if __name__ == "__main__":
    main()
