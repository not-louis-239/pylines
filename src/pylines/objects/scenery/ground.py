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

import ctypes

import numpy as np
import OpenGL.GL as gl
import pygame as pg

import pylines.core.constants as C
import pylines.core.paths as paths
from pylines.core.custom_types import Surface
from pylines.core.time_manager import brightness_from_hour, fetch_hour
from pylines.game.environment import Environment
from pylines.shaders.shader_manager import load_shader_script

from .bases import LargeSceneryObject


class Ground(LargeSceneryObject):
    def __init__(self, textures: dict[str, Surface], env: Environment) -> None:
        super().__init__(0, 0, 0)
        self.textures = {
            name: self._load_texture(surface)
            for name, surface in textures.items()
        }

        # Load and compile the shader program
        self.shader = load_shader_script(
            str(paths.SHADERS_DIR / "terrain.vert"),
            str(paths.SHADERS_DIR / "terrain.frag")
        )
        self.position_loc = gl.glGetAttribLocation(self.shader, "position")
        self.tex_coord_loc = gl.glGetAttribLocation(self.shader, "tex_coord")
        self.sea_level_loc = gl.glGetUniformLocation(self.shader, "sea_level")
        self.brightness_loc = gl.glGetUniformLocation(self.shader, "u_brightness")

        self.vbo = None
        self.ebo = None
        self.env = env
        self.grid_resolution = 400  # Number of vertices along one edge

        self.vertices: np.ndarray
        self.vertices, self.indices = self._build_mesh()
        self._setup_vbo()
        self._setup_ebo()

    def _build_mesh(self) -> tuple[np.ndarray, np.ndarray]:
        vertices = []
        indices = []

        res = self.grid_resolution
        step = C.HALF_WORLD_SIZE * 2 / res
        texture_scale = 200.0 / (C.HALF_WORLD_SIZE * 2)

        def vert_index(r: int, c: int) -> int:
            return r * (res + 1) + c

        # ---- vertices ----
        for r in range(res + 1):
            for c in range(res + 1):
                x = -C.HALF_WORLD_SIZE + c * step
                z = -C.HALF_WORLD_SIZE + r * step
                y = self.env.height_at(x, z)

                u = (x + C.HALF_WORLD_SIZE) * texture_scale
                v = (z + C.HALF_WORLD_SIZE) * texture_scale

                vertices.extend([x, y, z, u, v])

        # ---- indices ----
        for r in range(res):
            for c in range(res):
                vA = vert_index(r, c)
                vB = vert_index(r, c + 1)
                vC = vert_index(r + 1, c)
                vD = vert_index(r + 1, c + 1)

                indices.extend([vA, vB, vD])
                indices.extend([vA, vD, vC])

        return (
            np.array(vertices, dtype=np.float32),
            np.array(indices, dtype=np.uint32),
        )

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

        brightness = brightness_from_hour(fetch_hour())
        gl.glUniform1f(self.brightness_loc, brightness)

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
        gl.glUniform1f(self.sea_level_loc, self.env.sea_level)

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
