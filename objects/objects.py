import pygame as pg
from core.utils import Rotation
from OpenGL.GL import *   # type: ignore
from OpenGL.GLU import *  # type: ignore

from core.custom_types import Surface, Coord3
from core.constants import GROUND_SIZE

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

        self.pitch = 0
        self.yaw = 0
        self.roll = 0

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
        glPushMatrix()
        # Optional: Translate the ground if its position is not (0,0,0)
        # glTranslatef(self.pos.x, self.pos.y, self.pos.z)

        glBegin(GL_TRIANGLE_STRIP) # or GL_QUADS
        glColor3f(0.1, 0.35, 0.1) # Example: set a grey color for the ground
        for vertex in self.vertices:
            glVertex3f(*vertex)
        glEnd()
        glPopMatrix()