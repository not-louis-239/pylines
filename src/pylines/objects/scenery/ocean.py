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

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING

import numpy as np
import OpenGL.GL as gl
import pygame as pg

import pylines.core.constants as C
from pylines.core.paths import DIRECTORIES
from pylines.core.custom_types import Surface
from pylines.core.time_manager import fetch_hour, sunlight_strength_from_hour
from pylines.core.utils import lerp
from pylines.shaders.shader_manager import load_shader_script

from .bases import LargeSceneryObject

if TYPE_CHECKING:
    from pylines.game.environment import Environment


class Ocean(LargeSceneryObject):
    def __init__(self, image_surface: Surface, env: Environment) -> None:
        super().__init__(0, env.sea_level, 0)
        self.texture_id = self._load_texture(image_surface)
        self.env = env
        self.grid_resolution = 400  # Must match Ground for now
        self.texture_repeat_count = 25.0

        self.shader = load_shader_script(
            str(DIRECTORIES.src.shaders / "ocean.vert"),
            str(DIRECTORIES.src.shaders / "ocean.frag")
        )
        self.position_loc = gl.glGetAttribLocation(self.shader, "position")
        self.tex_coord_loc = gl.glGetAttribLocation(self.shader, "tex_coord")
        self.terrain_height_loc = gl.glGetAttribLocation(self.shader, "terrain_height")

        self.texture_loc = gl.glGetUniformLocation(self.shader, "u_texture")
        self.brightness_loc = gl.glGetUniformLocation(self.shader, "u_brightness")

        self.vertices: np.ndarray
        self.vertices, self.indices = self._build_mesh()
        self.vbo, self.ebo = self._setup_buffers()

    def _load_texture(self, image_surface: Surface) -> int:
        image_surface = pg.transform.flip(image_surface, False, True)
        image_data = pg.image.tostring(image_surface, "RGBA", True)
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, image_surface.get_width(), image_surface.get_height(), 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, image_data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        return texture_id

    def _build_mesh(self) -> tuple[np.ndarray, np.ndarray]:
        vertices = []
        indices = []

        res = self.grid_resolution
        step = C.HALF_WORLD_SIZE * 2 / res
        texture_scale = self.texture_repeat_count / (C.HALF_WORLD_SIZE * 2)

        def vert_index(r: int, c: int) -> int:
            return r * (res + 1) + c

        # ---- vertices ----
        for r in range(res + 1):
            for c in range(res + 1):
                x = -C.HALF_WORLD_SIZE + c * step
                z = -C.HALF_WORLD_SIZE + r * step
                y = self.env.sea_level
                terrain_y = self.env.height_at(x, z)

                u = (x + C.HALF_WORLD_SIZE) * texture_scale
                v = (z + C.HALF_WORLD_SIZE) * texture_scale

                vertices.extend([x, y, z, u, v, terrain_y])

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

    def _setup_buffers(self):
        vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, gl.GL_STATIC_DRAW)

        ebo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, ebo)
        gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, self.indices.nbytes, self.indices, gl.GL_STATIC_DRAW)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)

        return vbo, ebo

    def draw(self, cloud_attenuation: float):
        brightness = lerp(C.MOON_BRIGHTNESS, C.SUN_BRIGHTNESS, sunlight_strength_from_hour(fetch_hour()) * cloud_attenuation)

        gl.glPushMatrix()

        was_blend_enabled = gl.glIsEnabled(gl.GL_BLEND)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDepthMask(gl.GL_FALSE)  # Don't write to depth buffer

        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(-5.0, -5.0)

        gl.glUseProgram(self.shader)

        gl.glUniform1f(self.brightness_loc, brightness)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glUniform1i(self.texture_loc, 0)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ebo)

        stride = 6 * ctypes.sizeof(ctypes.c_float)
        gl.glEnableVertexAttribArray(self.position_loc)
        gl.glVertexAttribPointer(self.position_loc, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(0))

        gl.glEnableVertexAttribArray(self.tex_coord_loc)
        gl.glVertexAttribPointer(self.tex_coord_loc, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))

        gl.glEnableVertexAttribArray(self.terrain_height_loc)
        gl.glVertexAttribPointer(self.terrain_height_loc, 1, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(5 * ctypes.sizeof(ctypes.c_float)))

        gl.glDrawElements(gl.GL_TRIANGLES, len(self.indices), gl.GL_UNSIGNED_INT, None)

        gl.glDisableVertexAttribArray(self.position_loc)
        gl.glDisableVertexAttribArray(self.tex_coord_loc)
        gl.glDisableVertexAttribArray(self.terrain_height_loc)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)

        gl.glUseProgram(0)

        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)

        gl.glDepthMask(gl.GL_TRUE) # Re-enable depth writing
        if not was_blend_enabled:
            gl.glDisable(gl.GL_BLEND)

        gl.glPopMatrix()
