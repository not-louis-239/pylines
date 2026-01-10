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

from OpenGL import GL as gl, GLU as glu
import pygame as pg

from pylines.core.constants import GROUND_SIZE, WN_H, WN_W
from pylines.core.custom_types import Coord3, Surface
from pylines.objects.objects import Entity

class SceneryObject(Entity):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)

    def draw(self):
        raise NotImplementedError

class LargeSceneryObject(SceneryObject):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.vertices: list[Coord3] = [
            (-GROUND_SIZE, 0, -GROUND_SIZE),
            (-GROUND_SIZE, 0, GROUND_SIZE),
            (GROUND_SIZE, 0, -GROUND_SIZE),
            (GROUND_SIZE, 0, GROUND_SIZE)
        ]

    def draw(self):
        raise NotImplementedError

class CelestialObject(SceneryObject):
    def __init__(self, image_surface: Surface, direction: pg.Vector3, scale: float = 1.0):
        super().__init__(0, 0, 0)
        self.direction = direction.normalize()
        self.scale = scale
        self.texture_id = None
        self._load_texture(image_surface)

    def _load_texture(self, image_surface: Surface):
        image_surface = pg.transform.flip(image_surface, False, True)
        image_data = pg.image.tostring(image_surface, "RGBA", True)
        self.texture_id = gl.glGenTextures(1)

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, image_surface.get_width(), image_surface.get_height(), 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, image_data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def draw(self):
        distance = 19000.0
        size = 1500.0 * self.scale
        pos = self.direction * distance

        gl.glPushMatrix()

        # --- Save state ---
        was_blend_enabled = gl.glIsEnabled(gl.GL_BLEND)
        was_depth_mask_enabled = gl.glGetIntegerv(gl.GL_DEPTH_WRITEMASK)
        
        gl.glTranslatef(pos.x, pos.y, pos.z)

        # Billboard
        modelview = gl.glGetFloatv(gl.GL_MODELVIEW_MATRIX)
        inverse_rotation = [
            modelview[0][0], modelview[1][0], modelview[2][0], 0.0,
            modelview[0][1], modelview[1][1], modelview[2][1], 0.0,
            modelview[0][2], modelview[1][2], modelview[2][2], 0.0,
            0.0, 0.0, 0.0, 1.0,
        ]
        gl.glMultMatrixf(inverse_rotation)

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glColor4f(1.0, 1.0, 1.0, 1.0)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE)
        gl.glDepthMask(gl.GL_FALSE)

        gl.glBegin(gl.GL_QUADS)
        gl.glTexCoord2f(0, 0); gl.glVertex3f(-size, -size, 0)
        gl.glTexCoord2f(1, 0); gl.glVertex3f(size, -size, 0)
        gl.glTexCoord2f(1, 1); gl.glVertex3f(size, size, 0)
        gl.glTexCoord2f(0, 1); gl.glVertex3f(-size, size, 0)
        gl.glEnd()

        # --- Restore state ---
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glDepthMask(was_depth_mask_enabled)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA) # Restore default blend func
        if not was_blend_enabled:
            gl.glDisable(gl.GL_BLEND)

        gl.glPopMatrix()

class Ground(LargeSceneryObject):
    def __init__(self, image_surface: Surface) -> None:
        super().__init__(0, 0, 0)  # Initialize pos for Ground at origin
        self.texture_id = None
        self._load_texture(image_surface)

    def _load_texture(self, image_surface: Surface):
        # OpenGL textures are Y-flipped compared to Pygame
        image_surface = pg.transform.flip(image_surface, False, True)
        image_data = pg.image.tostring(image_surface, "RGBA", True)  # Get pixel data

        # Generate OpenGL texture ID
        self.texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)

        # Texture parameters
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT) # Repeat texture horizontally
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT) # Repeat texture vertically

        # Upload texture data to OpenGL
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, image_surface.get_width(), image_surface.get_height(), 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, image_data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0) # Unbind texture

    def draw(self):
        gl.glPushMatrix()

        # Enable polygon offset to prevent Z-fighting with other objects on the ground
        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(-1.0, -1.0)

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glColor3f(1.0, 1.0, 1.0) # Remove any potential color tint from glColor3f

        gl.glBegin(gl.GL_TRIANGLE_STRIP)

        # Assign texture coordinates (U, V) to each vertex
        texture_repeat_count = 1000  # Texture repeats over large ground
        gl.glTexCoord2f(0.0, 0.0); gl.glVertex3f(self.vertices[0][0], self.vertices[0][1], self.vertices[0][2])
        gl.glTexCoord2f(0.0, texture_repeat_count); gl.glVertex3f(self.vertices[1][0], self.vertices[1][1], self.vertices[1][2])
        gl.glTexCoord2f(texture_repeat_count, 0.0); gl.glVertex3f(self.vertices[2][0], self.vertices[2][1], self.vertices[2][2])
        gl.glTexCoord2f(texture_repeat_count, texture_repeat_count); gl.glVertex3f(self.vertices[3][0], self.vertices[3][1], self.vertices[3][2])
        gl.glEnd()

        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)  # Unbind texture

        # Disable polygon offset after drawing the ground
        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)

        gl.glPopMatrix()

class Sky(LargeSceneryObject):
    def __init__(self) -> None:
        super().__init__(0, 0, 0)  # Sky placed at origin

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

class Ocean(LargeSceneryObject):
    ...

# TODO: Expand scenery objects
# (when all core featuers have been implemented,
# and it is time to expand scenery)
class Building(SceneryObject): ...

class Sun(CelestialObject):
    def __init__(self, image_surface: Surface):
        direction = pg.Vector3(0.5, 0.5, -1)
        super().__init__(image_surface, direction, scale=0.5)

class Moon(CelestialObject):
    def __init__(self, image_surface: Surface):
        direction = pg.Vector3(-0.5, -0.5, 1)
        super().__init__(image_surface, direction, scale=0.5)