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


import math
from math import cos

import OpenGL.GL as gl
import OpenGL.GLU as glu
import pygame as pg
from noise import snoise2

import pylines.core.constants as C
from pylines.core.custom_types import Coord3, RealNumber, Surface
from pylines.core.time_manager import (
    fetch_hour,
    sun_direction_from_hour,
    sunlight_strength_from_hour,
)
from pylines.core.utils import clamp, lerp

from .bases import CelestialObject, LargeSceneryObject


class Sky(LargeSceneryObject):
    def __init__(self) -> None:
        super().__init__(0, 0, 0)  # Sky placed at origin

    def draw(self, colour_scheme) -> None:
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        glu.gluOrtho2D(0, C.WN_W, C.WN_H, 0)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()

        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glBegin(gl.GL_QUADS)
        # Top half (high to mid)
        gl.glColor3ub(*colour_scheme.high)
        gl.glVertex2f(0, 0)
        gl.glVertex2f(C.WN_W, 0)
        gl.glColor3ub(*colour_scheme.mid)
        gl.glVertex2f(C.WN_W, C.WN_H / 2)
        gl.glVertex2f(0, C.WN_H / 2)
        # Bottom half (mid to low)
        gl.glColor3ub(*colour_scheme.mid)
        gl.glVertex2f(0, C.WN_H / 2)
        gl.glVertex2f(C.WN_W, C.WN_H / 2)
        gl.glColor3ub(*colour_scheme.low)
        gl.glVertex2f(C.WN_W, C.WN_H)
        gl.glVertex2f(0, C.WN_H)
        gl.glEnd()
        gl.glEnable(gl.GL_DEPTH_TEST)

        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)

class Sun(CelestialObject):
    def __init__(self, image_surface: pg.Surface):
        super().__init__(image_surface, pg.Vector3(), scale=0.5)

    def set_direction(self, hour: float) -> None:
        """Set Sun direction based on hour (0-24).
        0 = directly underneath, 12 = directly overhead
        Sun rises in the east and sets in the west."""

        self.direction = sun_direction_from_hour(fetch_hour())

    def update(self):
        self.set_direction(fetch_hour())

class Moon(CelestialObject):
    def __init__(self, image_surface: pg.Surface):
        super().__init__(image_surface, pg.Vector3(), scale=0.5)

    def set_direction(self, hour: float) -> None:
        """Set Moon direction based on hour (0-24).
        Moon is opposite Sun."""

        self.direction = -sun_direction_from_hour(fetch_hour())

    def update(self):
        self.set_direction(fetch_hour())

class Star(CelestialObject):
    def __init__(
        self,
        direction: pg.Vector3,
        brightness: float = 1.0,
        colour: tuple[int, int, int] = (255, 255, 255),
        size: float = 1.0
    ) -> None:
        self.direction = direction  # currently represents offset from sun
        self.brightness = brightness
        self.colour = colour
        self.size = size

class CloudLayer(LargeSceneryObject):
    _SEED_SCALE = 157.3138214  # large, irrational-ish
    _X_OFFSET = 17.3
    _Z_OFFSET = 29.1

    def __init__(
        self, altitude: RealNumber, thickness: RealNumber, coverage: RealNumber,
        seed: RealNumber, cloud_tex: Surface
    ) -> None:
        super().__init__(0, 0, 0)
        self.altitude = altitude
        self.thickness = thickness
        self.coverage = coverage
        self.seed = seed
        self.cloud_tex = cloud_tex
        self._load_texture()

        # Precompute offsets for performance
        RADIUS = C.CLOUD_MAX_DRAW_RADIUS
        STEP = C.CLOUD_GRID_STEP
        self._grid_offsets = [
            (dx, dz)
            for dx in range(-RADIUS, RADIUS + 1, STEP)
            for dz in range(-RADIUS, RADIUS + 1, STEP)
        ]

        # Derive colour from coverage
        self.brightness = 1 - self.coverage * 0.5

        # Seed offsets
        self.sx = CloudLayer._SEED_SCALE * self.seed
        self.sz = CloudLayer._SEED_SCALE * self.seed * 0.7384

    def _draw_billboard(
        self, position: Coord3,
        size: RealNumber, alpha: RealNumber,
        camera_fwd: pg.Vector3
    ):
        base_brightness = lerp(C.MOON_BRIGHTNESS, C.SUN_BRIGHTNESS, sunlight_strength_from_hour(fetch_hour()))
        final_brightness = base_brightness * self.brightness

        size_half = size * 0.5

        # View direction from cloud to camera
        world_up = pg.Vector3(0, 1, 0)

        # Build billboard basis
        right = camera_fwd.cross(world_up)
        if right.length_squared() == 0:
            return
        right = right.normalize() * size_half

        up = right.cross(camera_fwd).normalize() * size_half

        gl.glColor4f(final_brightness, final_brightness, final_brightness, alpha)

        gl.glBegin(gl.GL_QUADS)

        gl.glTexCoord2f(0.0, 0.0)
        gl.glVertex3f(*(position - right - up))

        gl.glTexCoord2f(1.0, 0.0)
        gl.glVertex3f(*(position + right - up))

        gl.glTexCoord2f(1.0, 1.0)
        gl.glVertex3f(*(position + right + up))

        gl.glTexCoord2f(0.0, 1.0)
        gl.glVertex3f(*(position - right + up))

        gl.glEnd()

    def _load_texture(self):
        tex_data = pg.image.tostring(self.cloud_tex, "RGBA", True)

        self.texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)

        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

        # Upload texture data to OpenGL
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, *self.cloud_tex.get_size(), 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, tex_data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)  # Unbind texture

    def get_density(self, world_x: float, world_z: float):
        """Authoritative function to retrieve cloud
        density for a layer.

        Returns density value, noise-x and noise-z
        used in sampling."""

        wx, wz = world_x, world_z

        nx = wx * C.CLOUD_NOISE_SCALE + self.sx
        nz = wz * C.CLOUD_NOISE_SCALE + self.sz

        density = (snoise2(nx, nz) + 1.0) * 0.5
        return density, nx, nz

    def draw(self, camera_pos: pg.Vector3, camera_fwd: pg.Vector3):
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDepthMask(gl.GL_FALSE)
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)

        fwd_flat = pg.Vector3(camera_fwd.x, 0, camera_fwd.z).normalize()

        cx, _, cz = camera_pos

        base_x = cx - (cx % C.CLOUD_GRID_STEP)
        base_z = cz - (cz % C.CLOUD_GRID_STEP)

        threshold = 1 - self.coverage

        _cos_fov = cos(math.radians(C.FOV))

        for dx, dz in self._grid_offsets:
            # World coords - anchor to fixed grid to prevent popping
            wx = base_x + dx
            wz = base_z + dz

            to_blob = (pg.Vector3(wx - cx, 0, wz - cz))
            if to_blob.length() < C.EPSILON:
                continue

            to_blob.normalize_ip()

            # Forward cull
            if to_blob.dot(fwd_flat) < _cos_fov:
                continue

            density, nx, nz = self.get_density(wx, wz)
            if density < threshold:
                continue

            # Stable jitter to kill the grid
            jx = wx + snoise2(nx + CloudLayer._X_OFFSET, nz) * C.CLOUD_GRID_STEP * 0.35
            jz = wz + snoise2(nx, nz + CloudLayer._Z_OFFSET) * C.CLOUD_GRID_STEP * 0.35

            size = C.CLOUD_BASE_BLOB_SIZE * (0.9 + 0.7 * density)
            alpha = min(1, C.CLOUD_BASE_ALPHA * density)

            self._draw_billboard(
                position=(jx, self.altitude, jz),
                size=size,
                alpha=alpha,
                camera_fwd=camera_fwd
            )

        gl.glDisable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDepthMask(gl.GL_TRUE)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glDisable(gl.GL_TEXTURE_2D)
