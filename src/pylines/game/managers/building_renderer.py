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

import pylines.core.constants as C
from pylines.core.paths import DIRS
from pylines.core.time_manager import (
    fetch_hour,
    sun_direction_from_hour,
    sunlight_strength_from_hour,
)
from pylines.shaders.shader_manager import load_shader_script

if TYPE_CHECKING:
    from pylines.game.game import Game

class BuildingRenderer:
    def __init__(self, game: Game) -> None:
        self.game = game

        assert self.game.env is not None

        # Building rendering setup
        all_vertices = []
        for building in self.game.env.buildings:
            all_vertices.extend(building.get_vertices())

        if all_vertices:
            self.vertices = np.array(all_vertices, dtype=np.float32)
            self.vertex_count = len(self.vertices) // 10

            self.vbo = gl.glGenBuffers(1)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, gl.GL_STATIC_DRAW)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

            self.shader = load_shader_script(
                DIRS.src.shaders / "building.vert",
                DIRS.src.shaders / "building.frag"
            )
            self.pos_loc = gl.glGetAttribLocation(self.shader, "position")
            self.color_loc = gl.glGetAttribLocation(self.shader, "color")
            self.normal_loc = gl.glGetAttribLocation(self.shader, "normal")
            self.emissive_loc = gl.glGetAttribLocation(self.shader, "in_emissive")
            self.brightness_loc = gl.glGetUniformLocation(self.shader, "u_brightness")
            self.sun_direction_loc = gl.glGetUniformLocation(self.shader, "u_sun_direction")
            self.min_brightness_loc = gl.glGetUniformLocation(self.shader, "u_min_brightness")
            self.max_brightness_loc = gl.glGetUniformLocation(self.shader, "u_max_brightness")
            self.shade_multiplier_loc = gl.glGetUniformLocation(self.shader, "u_shade_multiplier")
        else:
            self.vertices = np.array([], dtype=np.float32)
            self.vertex_count = 0
            self.vbo = None

    def draw(self, cloud_attenuation: float) -> None:
        if not self.vertex_count or self.vbo is None:
            return

        gl.glUseProgram(self.shader)

        # Set uniforms
        current_hour = fetch_hour()
        brightness = sunlight_strength_from_hour(current_hour) * cloud_attenuation
        sun_direction = sun_direction_from_hour(current_hour)

        gl.glUniform1f(self.brightness_loc, brightness)
        gl.glUniform3f(self.sun_direction_loc, sun_direction.x, sun_direction.y, sun_direction.z)
        gl.glUniform1f(self.min_brightness_loc, C.MOON_BRIGHTNESS)
        gl.glUniform1f(self.max_brightness_loc, C.SUN_BRIGHTNESS)
        gl.glUniform1f(self.shade_multiplier_loc, C.SHADE_BRIGHTNESS_MULT)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)

        stride = 10 * ctypes.sizeof(ctypes.c_float)

        # Position
        gl.glEnableVertexAttribArray(self.pos_loc)
        gl.glVertexAttribPointer(self.pos_loc, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(0))

        # Color
        gl.glEnableVertexAttribArray(self.color_loc)
        gl.glVertexAttribPointer(self.color_loc, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))

        # Normal
        gl.glEnableVertexAttribArray(self.normal_loc)
        gl.glVertexAttribPointer(self.normal_loc, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(6 * ctypes.sizeof(ctypes.c_float)))

        # Emissive
        gl.glEnableVertexAttribArray(self.emissive_loc)
        gl.glVertexAttribPointer(self.emissive_loc, 1, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(9 * ctypes.sizeof(ctypes.c_float)))

        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self.vertex_count)

        gl.glDisableVertexAttribArray(self.pos_loc)
        gl.glDisableVertexAttribArray(self.color_loc)
        gl.glDisableVertexAttribArray(self.normal_loc)
        gl.glDisableVertexAttribArray(self.emissive_loc)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glUseProgram(0)