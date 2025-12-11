import pygame as pg
import OpenGL.GL as gl
import OpenGL.GLU as glu

from core.custom_types import Surface, Coord3
from core.constants import GROUND_SIZE, WN_W, WN_H # Import WN_W, WN_H

class Entity:
    """Mental basis for all in-game physical objects"""

    def __init__(self, x, y, z) -> None:
        self.pos = pg.Vector3(x, y, z)

    def update(self):
        pass

    def draw(self, wn: Surface):
        pass

class Plane(Entity):
    def __init__(self):
        self.pos = pg.Vector3(0, 0, 0)
        self.vel = pg.Vector3(0, 0, 0)
        self.acc = pg.Vector3(0, 0, 0)

        self.rot = pg.Vector3(0, 0, 0)  # Pitch, yaw, roll

        self.throttle = 0
        self.flaps = 0
        self.engine_on = True

class Ground(Entity):
    def __init__(self) -> None:
        super().__init__(0, 0, 0) # Initialize pos for Ground at origin
        self.vertices: list[Coord3] = [
            (-GROUND_SIZE, 0, -GROUND_SIZE),
            (-GROUND_SIZE, 0, GROUND_SIZE),
            (GROUND_SIZE, 0, -GROUND_SIZE),
            (GROUND_SIZE, 0, GROUND_SIZE)
        ]

    def draw(self): # The `wn` parameter might not be necessary for OpenGL rendering
        gl.glPushMatrix()

        gl.glBegin(gl.GL_TRIANGLE_STRIP)
        gl.glColor3f(0.1, 0.35, 0.1)
        for vertex in self.vertices:
            gl.glVertex3f(*vertex)
        gl.glEnd()
        gl.glPopMatrix()

class Sky(Entity):
    def __init__(self) -> None:
        super().__init__(0, 0, 0) # Sky is at origin

    def draw(self, colour_scheme) -> None:
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        glu.gluOrtho2D(0, WN_W, WN_H, 0)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()

        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glBegin(gl.GL_QUADS)
        # Top half (high to mid)
        gl.glColor3ub(*colour_scheme.high)
        gl.glVertex2f(0, 0)
        gl.glVertex2f(WN_W, 0)
        gl.glColor3ub(*colour_scheme.mid)
        gl.glVertex2f(WN_W, WN_H / 2)
        gl.glVertex2f(0, WN_H / 2)
        # Bottom half (mid to low)
        gl.glColor3ub(*colour_scheme.mid)
        gl.glVertex2f(0, WN_H / 2)
        gl.glVertex2f(WN_W, WN_H / 2)
        gl.glColor3ub(*colour_scheme.low)
        gl.glVertex2f(WN_W, WN_H)
        gl.glVertex2f(0, WN_H)
        gl.glEnd()
        gl.glEnable(gl.GL_DEPTH_TEST)

        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)