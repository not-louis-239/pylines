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
from math import cos, sin

import OpenGL.GL as gl
import OpenGL.GLU as glu
import pygame as pg

import pylines.core.constants as C
from pylines.core.time_manager import fetch_hour

from .bases import CelestialObject, LargeSceneryObject
from pylines.core.utils import clamp

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

        pi = math.pi

        azimuth = (-pi/2 + 2*pi * hour/24) % (2*pi)  # radians, with 0 = east
        elevation = sin((hour - 6) * (2*pi / 24))   # -1 = directly underneath, 1 = directly overhead

        h = (1 - elevation**2)**0.5
        self.direction = pg.Vector3(
            h * cos(azimuth),  # X
            elevation,         # Y
            -h * sin(azimuth)  # Z
        )

    def update(self):
        self.set_direction(fetch_hour())

class Moon(CelestialObject):
    def __init__(self, image_surface: pg.Surface):
        super().__init__(image_surface, pg.Vector3(), scale=0.5)

    def set_direction(self, hour: float) -> None:
        """Set Moon direction based on hour (0-24).
        Moon is opposite Sun."""

        pi = math.pi

        azimuth = (-pi/2 + 2*pi * hour/24) % (2*pi)  # radians, with 0 = east
        elevation = sin((hour - 6) * (2*pi / 24))   # -1 = directly underneath, 1 = directly overhead

        h = (1 - elevation**2)**0.5
        self.direction = pg.Vector3(
            h * cos(azimuth),  # X
            elevation,         # Y
            -h * sin(azimuth)  # Z
        )
        self.direction *= -1

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
        self.direction = direction
        self.brightness = brightness
        self.colour = colour
        self.size = size

    def draw(self, camera_fwd: pg.Vector3) -> None:
        """Stars should draw at full opacity during the night
        and not be visible before sunset."""

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

        distance = 19000.0
        pos = self.direction * distance # Star's position in world coordinates

        if camera_fwd.dot(self.direction) <= cos(math.radians(45)):  # Cull based on FOV
            return

        gl.glPushMatrix()

        # Save OpenGL states
        was_blend_enabled = gl.glIsEnabled(gl.GL_BLEND)
        was_depth_mask_enabled = gl.glGetBooleanv(gl.GL_DEPTH_WRITEMASK)
        current_point_size = gl.glGetFloatv(gl.GL_POINT_SIZE)
        was_texture_2d_enabled = gl.glIsEnabled(gl.GL_TEXTURE_2D)

        # Set states for drawing the star
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDepthMask(gl.GL_FALSE)
        gl.glDisable(gl.GL_TEXTURE_2D)

        gl.glTranslatef(pos.x, pos.y, pos.z)

        gl.glPointSize(self.size)
        gl.glColor4f(
            self.colour[0] / 255.0,
            self.colour[1] / 255.0,
            self.colour[2] / 255.0,
            opacity * self.brightness
        )

        gl.glBegin(gl.GL_POINTS)
        gl.glVertex3f(0, 0, 0)
        gl.glEnd()

        # Restore OpenGL states
        gl.glPointSize(current_point_size)
        gl.glDepthMask(was_depth_mask_enabled)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        if was_texture_2d_enabled:
            gl.glEnable(gl.GL_TEXTURE_2D)
        if not was_blend_enabled:
            gl.glDisable(gl.GL_BLEND)

        gl.glPopMatrix()