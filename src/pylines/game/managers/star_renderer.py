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

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL as gl

import pylines.core.constants as C
from pylines.core.time_manager import (
    fetch_hour,
    sun_direction_from_hour,
)
from pylines.core.utils import clamp
from pylines.game.environment import Environment
from pylines.objects.objects import Plane

if TYPE_CHECKING:
    pass

@dataclass
class StarRenderingData:
    dirs: np.ndarray | None = None
    colors: np.ndarray | None = None
    brightness: np.ndarray | None = None
    base_positions: np.ndarray | None = None
    vbo: int | None = None
    color_vbo: int | None = None
    count: int = 0
    cache_key: tuple[float, float] | None = None

class StarRenderer:
    def __init__(self, data: StarRenderingData, env: Environment, plane: Plane) -> None:
        self.data = data  # Internal rendering data
        self.env = env
        self.plane = plane

    def draw_stars(self) -> None:
        assert self.env is not None

        hour = fetch_hour()
        if 18 >= hour > 6:  # daytime
            opacity = 0
        elif 20 >= hour > 18:  # sunset
            opacity = (hour - 18) / 2
        elif 6 >= hour > 4:  # sunrise
            opacity = 1 - (hour - 4) / 2
        else:  # night
            opacity = 1

        opacity = clamp(opacity, (0, 1))
        if opacity == 0:
            return

        # Initialize star buffers if needed
        if self.data.dirs is None:
            dirs = np.array([s.direction for s in self.env.stars], dtype=np.float32)
            # Normalize directions once safely
            norms = np.linalg.norm(dirs, axis=1, keepdims=True)
            norms[norms == 0] = 1
            self.data.dirs = dirs / norms
            self.data.colors = np.array([s.colour for s in self.env.stars], dtype=np.float32) / 255.0
            self.data.brightness = np.array([s.brightness for s in self.env.stars], dtype=np.float32)
            self.data.count = len(self.env.stars)

            # Create VBOs
            self.data.vbo = gl.glGenBuffers(1)
            self.data.color_vbo = gl.glGenBuffers(1)

        # Cache base positions when hour bucket or opacity changes; apply camera offset each frame
        assert self.data.brightness is not None
        assert self.data.dirs is not None

        hour_bucket = round(fetch_hour(), 2)
        cache_key = (hour_bucket, round(opacity, 3))
        if self.data.cache_key != cache_key or self.data.base_positions is None:
            sun_dir = sun_direction_from_hour(hour_bucket)
            ref_dir = np.array([0.0, 0.0, -1.0], dtype=np.float32)
            sun = np.array([sun_dir.x, sun_dir.y, sun_dir.z], dtype=np.float32)

            k = np.cross(ref_dir, sun)
            k_norm = np.linalg.norm(k)
            if k_norm < C.MATH_EPSILON:
                if np.dot(ref_dir, sun) > 0:
                    rotated = self.data.dirs
                else:
                    rotated = -self.data.dirs
            else:
                k = k / k_norm
                cos_theta = np.clip(np.dot(ref_dir, sun), -1.0, 1.0)
                theta = math.acos(cos_theta)
                sin_t = math.sin(theta)
                v = self.data.dirs
                rotated = (
                    v * cos_theta +
                    np.cross(k, v) * sin_t +
                    k * (np.dot(v, k))[:, None] * (1 - cos_theta)
                )

            norms = np.linalg.norm(rotated, axis=1, keepdims=True)
            norms[norms == 0] = 1
            self.data.base_positions = (rotated / norms) * 1000

            colors = np.empty((self.data.count, 4), dtype=np.float32)
            colors[:, :3] = self.data.colors
            colors[:, 3] = self.data.brightness * opacity

            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.data.color_vbo)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, colors.nbytes, colors, gl.GL_DYNAMIC_DRAW)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

            self.data.cache_key = cache_key

        assert self.data.base_positions is not None
        camera_pos = np.array(
            [self.plane.pos.x, self.plane.pos.y + C.CAMERA_RADIUS, self.plane.pos.z],
            dtype=np.float32,
        )
        positions = self.data.base_positions + camera_pos

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.data.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, positions.nbytes, positions, gl.GL_DYNAMIC_DRAW)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

        # Save OpenGL states
        was_blend_enabled = gl.glIsEnabled(gl.GL_BLEND)
        was_depth_mask_enabled = gl.glGetBooleanv(gl.GL_DEPTH_WRITEMASK)
        was_depth_test_enabled = gl.glIsEnabled(gl.GL_DEPTH_TEST)
        current_point_size = gl.glGetFloatv(gl.GL_POINT_SIZE)
        was_texture_2d_enabled = gl.glIsEnabled(gl.GL_TEXTURE_2D)

        # Configure GL for point rendering
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDepthMask(gl.GL_FALSE)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glPointSize(2.0)

        # Enable vertex/color arrays
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_COLOR_ARRAY)

        # Bind VBOs
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.data.vbo)
        gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.data.color_vbo)
        gl.glColorPointer(4, gl.GL_FLOAT, 0, None)

        # Draw stars
        gl.glDrawArrays(gl.GL_POINTS, 0, self.data.count)

        # Cleanup
        gl.glDisableClientState(gl.GL_COLOR_ARRAY)
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

        # Restore OpenGL states
        if was_depth_test_enabled:
            gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glPointSize(current_point_size)
        gl.glDepthMask(was_depth_mask_enabled)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        if was_texture_2d_enabled:
            gl.glEnable(gl.GL_TEXTURE_2D)
        if not was_blend_enabled:
            gl.glDisable(gl.GL_BLEND)
