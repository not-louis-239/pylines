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
import numpy as np
import ctypes
import numpy as np

from pylines.core.asset_manager import MapData
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
    def __init__(self, image_surface: Surface, map_data: MapData) -> None:
        super().__init__(0, 0, 0)
        self.texture_id = None
        self._load_texture(image_surface)

        self.map_data = map_data
        self.vbo = None
        self.ebo = None
        self.grid_resolution = 200 # Number of vertices along one edge
        self.vertices = self._create_vertex_grid()
        self.indices = self._create_index_buffer()
        self._setup_vbo()
        self._setup_ebo()

    def _create_vertex_grid(self):
        # We need to store vertices and texture coordinates
        # Each vertex will have (x, y, z, u, v)
        data = []
        step = GROUND_SIZE * 2 / self.grid_resolution
        # The texture_repeat_count from the old draw method implies 200 repeats over GROUND_SIZE*2 extent
        # So one repeat covers (GROUND_SIZE * 2) / 200 = GROUND_SIZE / 100
        # The U, V coordinates should reflect this
        texture_scale_factor = 200.0 / (GROUND_SIZE * 2) # How many texture repeats per world unit

        for i in range(self.grid_resolution + 1):
            for j in range(self.grid_resolution + 1):
                x = -GROUND_SIZE + j * step
                z = -GROUND_SIZE + i * step
                y = self.map_data.get_height(x, z)

                # Calculate texture coordinates (u, v)
                u = (x + GROUND_SIZE) * texture_scale_factor
                v = (z + GROUND_SIZE) * texture_scale_factor

                data.extend([x, y, z, u, v])
        return np.array(data, dtype=np.float32)

    def _create_index_buffer(self):
        indices = []
        # Loop through rows of the grid
        for i in range(self.grid_resolution):
            # For each row, loop through columns
            for j in range(self.grid_resolution + 1):
                # Add vertex from current row
                indices.append(i * (self.grid_resolution + 1) + j)
                # Add vertex from next row
                indices.append((i + 1) * (self.grid_resolution + 1) + j)
            # Add degenerate triangles to connect strips
            # if it's not the last row
            if i != self.grid_resolution - 1:
                indices.append((i + 1) * (self.grid_resolution + 1) + self.grid_resolution)
                indices.append((i + 1) * (self.grid_resolution + 1))
        return np.array(indices, dtype=np.uint32)

    def _setup_vbo(self):
        # Create a buffer object
        self.vbo = gl.glGenBuffers(1)
        # Bind the buffer
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        # Upload the data
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, gl.GL_STATIC_DRAW)
        # Unbind the buffer
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

    def _setup_ebo(self):
        # Create a buffer object
        self.ebo = gl.glGenBuffers(1)
        # Bind the buffer
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        # Upload the data
        gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, self.indices.nbytes, self.indices, gl.GL_STATIC_DRAW)
        # Unbind the buffer
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)

    def get_height(self, x: float, z: float) -> float:
        return self.map_data.get_height(x, z)

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

        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(-1.0, -1.0)

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glColor3f(1.0, 1.0, 1.0)

        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ebo)

        # Stride is 5 * sizeof(float) because each vertex has x,y,z,u,v
        # Vertex position is at offset 0
        gl.glVertexPointer(3, gl.GL_FLOAT, self.vertices.itemsize * 5, ctypes.c_void_p(0))
        # Texture coordinates are at offset 3 * sizeof(float)
        gl.glTexCoordPointer(2, gl.GL_FLOAT, self.vertices.itemsize * 5, ctypes.c_void_p(self.vertices.itemsize * 3))

        gl.glDrawElements(gl.GL_TRIANGLE_STRIP, len(self.indices), gl.GL_UNSIGNED_INT, None)

        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)

        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

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

# TODO: Expand building objects once heightmap implementation is done
class Building(SceneryObject): ...

class Sun(CelestialObject):
    def __init__(self, image_surface: Surface):
        direction = pg.Vector3(0.5, 0.5, -1)
        super().__init__(image_surface, direction, scale=0.5)

class Moon(CelestialObject):
    def __init__(self, image_surface: Surface):
        direction = pg.Vector3(-0.5, -0.5, 1)
        super().__init__(image_surface, direction, scale=0.5)