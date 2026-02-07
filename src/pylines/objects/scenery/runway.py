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

import OpenGL.GL as gl
import pygame as pg

from pylines.core.asset_manager import Fonts
from pylines.core.constants import MOON_BRIGHTNESS, SUN_BRIGHTNESS
from pylines.core.custom_types import Surface
from pylines.core.time_manager import fetch_hour, sunlight_strength_from_hour
from pylines.core.utils import draw_text, lerp

from .bases import LargeSceneryObject


class Runway(LargeSceneryObject):
    def __init__(
        self, name: str, x: float, y: float, z: float, w: float, l: float, heading: float,
        fonts: Fonts, texture: Surface
    ) -> None:
        super().__init__(x, y, z)
        self.name = name
        self.w = w
        self.l = l
        self.heading = heading

        self.texture_id = None
        self._load_texture(fonts, texture)

    def _load_texture(self, fonts: Fonts, texture: Surface):
        # Design texture
        texture_surface = pg.Surface((int(self.w * 4), int(self.l * 4)))  # allow detailed texture
        texture_surface.fill((0, 0, 0, 255))
        texture_surface.blit(pg.transform.scale_by(pg.transform.rotate(texture.convert_alpha(), 90), 4), (0, 0))

        # Edge stripes
        r = pg.Rect(0, 0, 10, int(self.l * 4)); pg.draw.rect(texture_surface, (243, 243, 243, 255), r)
        r = pg.Rect(int(self.w * 4) - 10, 0, 10, int(self.l * 4)); pg.draw.rect(texture_surface, (243, 243, 243, 255), r)

        # Threshold bars
        r = pg.Rect(0, 0, int(self.w * 4), 10); pg.draw.rect(texture_surface, (243, 243, 243, 255), r)
        r = pg.Rect(0, int(self.l * 4) - 10, int(self.w * 4), 10); pg.draw.rect(texture_surface, (243, 243, 243, 255), r)

        # Centreline
        for i in range(300, int(self.l * 4 - 300) + 1, 100):
            r = pg.Rect(int(self.w * 4) / 2 - 5, 25 + i, 10, 50); pg.draw.rect(texture_surface, (243, 243, 243, 255), r)

        # Runway numbers
        if self.heading >= 180:
            raise ValueError(f"Base heading must be <180°, e.g. {self.heading-180}°, not {self.heading}°.")  # keep things consistent

        draw_text(texture_surface, (int(self.w * 4) / 2, 150), 'centre', 'centre', str(round(self.heading/10)), (255, 255, 255, 255), 150, fonts.monospaced, rotation=180)
        draw_text(texture_surface, (int(self.w * 4) / 2, int(self.l * 4) - 150), 'centre', 'centre', str((round(self.heading/10) + 18) % 36), (255, 255, 255, 255), 150, fonts.monospaced)

        # Flip the surface vertically for OpenGL
        image_surface = pg.transform.flip(texture_surface, False, True)
        image_data = pg.image.tostring(image_surface, "RGBA", True)

        # Generate OpenGL texture ID
        self.texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)

        # Texture parameters
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

        # Upload texture data to OpenGL
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, image_surface.get_width(), image_surface.get_height(), 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, image_data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)  # Unbind texture

    def draw(self, cloud_attenuation):
        brightness = lerp(MOON_BRIGHTNESS, SUN_BRIGHTNESS, sunlight_strength_from_hour(fetch_hour()) * cloud_attenuation)
        gl.glPushMatrix()

        # Save current blend and depth mask states to restore them later
        was_blend_enabled = gl.glIsEnabled(gl.GL_BLEND)
        was_depth_mask_enabled = gl.glGetIntegerv(gl.GL_DEPTH_WRITEMASK)

        # Enable texturing and blending for textured quad
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDepthMask(gl.GL_FALSE)  # Don't write to depth buffer for transparent parts

        # Apply daylight brightness to the texture color
        gl.glColor4f(brightness, brightness, brightness, 1.0)

        # Enable polygon offset to "pull" the runway towards the camera
        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(-6.0, -6.0)

        # Translate and rotate to runway's position and heading
        gl.glTranslatef(self.pos.x, 0.2 + self.pos.y, self.pos.z)  # small offset prevents z-fighting
        gl.glRotatef(-self.heading, 0, 1, 0)  # rotation flipped in OpenGL

        half_width = self.w / 2
        half_length = self.l / 2

        gl.glBegin(gl.GL_QUADS)
        gl.glTexCoord2f(0, 0); gl.glVertex3f(-half_width, 0, -half_length) # Bottom-left
        gl.glTexCoord2f(1, 0); gl.glVertex3f(half_width, 0, -half_length)  # Bottom-right
        gl.glTexCoord2f(1, 1); gl.glVertex3f(half_width, 0, half_length)   # Top-right
        gl.glTexCoord2f(0, 1); gl.glVertex3f(-half_width, 0, half_length)  # Top-left
        gl.glEnd()

        # Restore states
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glDisable(gl.GL_TEXTURE_2D)

        gl.glDepthMask(was_depth_mask_enabled)  # Restore depth writing
        if not was_blend_enabled:  # Only disable blend if it was disabled before
            gl.glDisable(gl.GL_BLEND)

        # Disable polygon offset
        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)

        gl.glPopMatrix()
