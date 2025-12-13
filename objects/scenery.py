import pygame as pg
import OpenGL.GL as gl
import OpenGL.GLU as glu

from objects.objects import Entity
from core.custom_types import Surface, Coord3
from core.constants import GROUND_SIZE, WN_H, WN_W

# TODO: This is unused, will come in useful when I add buildings and other more advanced scenery
class SceneryObject:
    def __init__(self, pos: pg.Vector3):
        self.position = pos

    def draw(self):
        raise NotImplementedError

class Ground(Entity):
    def __init__(self, image_surface: Surface) -> None:
        super().__init__(0, 0, 0) # Initialize pos for Ground at origin
        self.vertices: list[Coord3] = [
            (-GROUND_SIZE, 0, -GROUND_SIZE),
            (-GROUND_SIZE, 0, GROUND_SIZE),
            (GROUND_SIZE, 0, -GROUND_SIZE),
            (GROUND_SIZE, 0, GROUND_SIZE)
        ]
        self.texture_id = None
        self._load_texture(image_surface)

    def _load_texture(self, image_surface: Surface):
        # OpenGL textures are often Y-flipped compared to Pygame
        image_surface = pg.transform.flip(image_surface, False, True)
        image_data = pg.image.tostring(image_surface, "RGBA", True) # Get pixel data

        # Generate OpenGL texture ID
        self.texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)

        # Set texture parameters
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT) # Repeat texture horizontally
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT) # Repeat texture vertically

        # Upload texture data to OpenGL
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, image_surface.get_width(), image_surface.get_height(), 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, image_data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0) # Unbind texture

    def draw(self): # The `wn` parameter might not be necessary for OpenGL rendering
        gl.glPushMatrix()

        # Enable polygon offset to prevent Z-fighting with other objects on the ground
        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(-1.0, -1.0)

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glColor3f(1.0, 1.0, 1.0) # Ensure no color tint from glColor3f

        gl.glBegin(gl.GL_TRIANGLE_STRIP)
        # Assign texture coordinates (U, V) to each vertex
        # The 10.0 here makes the texture repeat 10 times across the ground plane
        texture_repeat_count = 1000  # Make texture repeat many times over large ground
        gl.glTexCoord2f(0.0, 0.0); gl.glVertex3f(self.vertices[0][0], self.vertices[0][1], self.vertices[0][2])
        gl.glTexCoord2f(0.0, texture_repeat_count); gl.glVertex3f(self.vertices[1][0], self.vertices[1][1], self.vertices[1][2])
        gl.glTexCoord2f(texture_repeat_count, 0.0); gl.glVertex3f(self.vertices[2][0], self.vertices[2][1], self.vertices[2][2])
        gl.glTexCoord2f(texture_repeat_count, texture_repeat_count); gl.glVertex3f(self.vertices[3][0], self.vertices[3][1], self.vertices[3][2])
        gl.glEnd()

        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0) # Unbind texture

        # Disable polygon offset after drawing the ground
        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)

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

# TODO: Expand these when the time is right
# (when all core featuers have been implemented,
# and it is time to expand scenery)
class Building(SceneryObject): ...
class CelestialObject(SceneryObject): ...
class Sun(CelestialObject): ...
class Moon(CelestialObject): ...