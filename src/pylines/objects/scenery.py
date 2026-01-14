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

from typing import TYPE_CHECKING

from OpenGL import GL as gl, GLU as glu
import pygame as pg
import numpy as np
import ctypes
import numpy as np

from pylines.core.constants import WORLD_SIZE, WN_H, WN_W
from pylines.core.custom_types import Coord3, Surface, RealNumber
from pylines.objects.objects import Entity

from pylines.shaders.shader_manager import load_shader_script

if TYPE_CHECKING:
    from pylines.core.heightmap import Heightmap

class SceneryObject(Entity):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)

    def draw(self):
        raise NotImplementedError

class LargeSceneryObject(SceneryObject):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.vertices: list[Coord3] = [
            (-WORLD_SIZE, 0, -WORLD_SIZE),
            (-WORLD_SIZE, 0, WORLD_SIZE),
            (WORLD_SIZE, 0, -WORLD_SIZE),
            (WORLD_SIZE, 0, WORLD_SIZE)
        ]

    def draw(self):
        raise NotImplementedError

class CelestialObject(SceneryObject):
    """Reserved for objects that are so far away that
    their position virtually does not change in the sky
    based on location, such as the sun and moon."""

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
    def __init__(self, textures: dict[str, Surface], heightmap: Heightmap) -> None:
        super().__init__(0, 0, 0)
        self.textures = {
            name: self._load_texture(surface)
            for name, surface in textures.items()
        }

        # Load and compile the shader program
        self.shader = load_shader_script(
            "src/pylines/shaders/terrain.vert",
            "src/pylines/shaders/terrain.frag"
        )
        self.position_loc = gl.glGetAttribLocation(self.shader, "position")
        self.tex_coord_loc = gl.glGetAttribLocation(self.shader, "tex_coord")
        self.sea_level_loc = gl.glGetUniformLocation(self.shader, "sea_level")

        self.vbo = None
        self.ebo = None
        self.grid_resolution = 400  # Number of vertices along one edge
        self.heightmap = heightmap
        self.vertices: np.ndarray = self._create_vertex_grid()
        self.indices = self._create_index_buffer()
        self._setup_vbo()
        self._setup_ebo()

    def _create_vertex_grid(self) -> np.ndarray:
        # We need to store vertices and texture coordinates
        # Each vertex will have (x, y, z, u, v)
        data = []
        step = WORLD_SIZE * 2 / self.grid_resolution

        # The texture_repeat_count from the old draw method implies 200 repeats over GROUND_SIZE*2 extent
        # So one repeat covers (GROUND_SIZE * 2) / 200 = GROUND_SIZE / 100
        # The U, V coordinates should reflect this
        texture_scale_factor = 200.0 / (WORLD_SIZE * 2) # How many texture repeats per world unit

        for i in range(self.grid_resolution + 1):
            for j in range(self.grid_resolution + 1):
                x = -WORLD_SIZE + j * step
                z = -WORLD_SIZE + i * step
                y = self.heightmap.height_at(x, z)

                # Calculate texture coordinates (u, v)
                u = (x + WORLD_SIZE) * texture_scale_factor
                v = (z + WORLD_SIZE) * texture_scale_factor

                data.extend([x, y, z, u, v])
        return np.array(data, dtype=np.float32)

    def _create_index_buffer(self):
        indices = []
        rows = self.grid_resolution
        cols = self.grid_resolution
        for r in range(rows):
            for c in range(cols):
                # Get indices for the four corners of the quad
                # A: top-left (r, c)
                # B: top-right (r, c+1)
                # C: bottom-left (r+1, c)
                # D: bottom-right (r+1, c+1)
                A = r * (cols + 1) + c
                B = r * (cols + 1) + c + 1
                C = (r + 1) * (cols + 1) + c
                D = (r + 1) * (cols + 1) + c + 1

                # Triangle 1: ABD (split along AD)
                indices.append(A)
                indices.append(B)
                indices.append(D)

                # Triangle 2: ACD (split along AD)
                indices.append(A)
                indices.append(D)
                indices.append(C)
        return np.array(indices, dtype=np.uint32)

    def _setup_vbo(self):
        # Create a buffer object
        self.vbo = gl.glGenBuffers(1)
        # Bind the buffer
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        # Upload the data
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, gl.GL_STATIC_DRAW)  # type: ignore[arg-type]
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

    def _load_texture(self, image_surface: Surface) -> int:
        # OpenGL textures are Y-flipped compared to Pygame
        image_surface = pg.transform.flip(image_surface, False, True)
        image_data = pg.image.tostring(image_surface, "RGBA", True)  # Get pixel data

        # Generate OpenGL texture ID
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)

        # Texture parameters
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT) # Repeat texture horizontally
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT) # Repeat texture vertically

        # Upload texture data to OpenGL
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, image_surface.get_width(), image_surface.get_height(), 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, image_data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0) # Unbind texture
        return texture_id

    def draw(self):
        gl.glPushMatrix()

        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(-1.0, -1.0)  # or else terrain segments z-fight among themselves

        gl.glEnable(gl.GL_TEXTURE_2D)  # Enable texturing before using shaders
        gl.glUseProgram(self.shader)  # Activate the shader program

        # Set up textures for the shader
        for i, (name, texture_id) in enumerate(self.textures.items()):
            gl.glActiveTexture(gl.GL_TEXTURE0 + i)  # type: ignore[arg-type]
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
            location = gl.glGetUniformLocation(self.shader, name)
            gl.glUniform1i(location, i)

        # Add greyscale noise texture
        gl.glActiveTexture(gl.GL_TEXTURE6)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.textures["noise"])
        gl.glUniform1i(gl.glGetUniformLocation(self.shader, "noise_texture"), 6)

        # Pass sea level to shader
        gl.glUniform1f(self.sea_level_loc, self.heightmap.sea_level)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ebo)

        # Enable and define vertex attributes
        stride = self.vertices.itemsize * 5
        gl.glEnableVertexAttribArray(self.position_loc)
        gl.glVertexAttribPointer(self.position_loc, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(0))

        gl.glEnableVertexAttribArray(self.tex_coord_loc)
        gl.glVertexAttribPointer(self.tex_coord_loc, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(self.vertices.itemsize * 3))

        gl.glDrawElements(gl.GL_TRIANGLES, len(self.indices), gl.GL_UNSIGNED_INT, None)

        # Disable vertex attributes
        gl.glDisableVertexAttribArray(self.position_loc)
        gl.glDisableVertexAttribArray(self.tex_coord_loc)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)

        gl.glUseProgram(0) # Deactivate shader
        # Unbind textures and reset active texture unit
        for i in range(len(self.textures)):
            gl.glActiveTexture(gl.GL_TEXTURE0 + i)  # type: ignore[arg-type]
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glActiveTexture(gl.GL_TEXTURE0) # Reset to default texture unit
        gl.glDisable(gl.GL_TEXTURE_2D) # Disable texturing after using shaders

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
    def __init__(self, image_surface: Surface, sea_level: RealNumber) -> None:
        super().__init__(0, sea_level, 0)
        self.texture_id = None
        self._load_texture(image_surface)
        self.texture_repeat_count = 25.0  # Low repeat count for object

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
        gl.glPolygonOffset(1.0, 1.0)  # Push ocean away, ocean should lose ties with ground

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glColor3f(1.0, 1.0, 1.0)

        gl.glBegin(gl.GL_QUADS)
        # Using vertices from LargeSceneryObject, re-ordered
        gl.glTexCoord2f(0, 0)
        gl.glVertex3f(-WORLD_SIZE, 0, -WORLD_SIZE)

        gl.glTexCoord2f(self.texture_repeat_count, 0)
        gl.glVertex3f(WORLD_SIZE, 0, -WORLD_SIZE)

        gl.glTexCoord2f(self.texture_repeat_count, self.texture_repeat_count)
        gl.glVertex3f(WORLD_SIZE, 0, WORLD_SIZE)

        gl.glTexCoord2f(0, self.texture_repeat_count)
        gl.glVertex3f(-WORLD_SIZE, 0, WORLD_SIZE)
        gl.glEnd()

        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPopMatrix()

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
