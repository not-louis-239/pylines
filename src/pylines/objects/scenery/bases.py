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

from pylines.objects.objects import Entity
from pylines.objects.building_parts import BuildingPart

import OpenGL.GL as gl
from pylines.core.custom_types import Surface
import pylines.core.constants as C
import pygame as pg

class SceneryObject(Entity):
    """Base class for all scenery objects. Visual or structural
    elements of the world that do not represent living entities."""

    def __init__(self, x, y, z):
        super().__init__(x, y, z)

    def draw(self):
        raise NotImplementedError

class SmallSceneryObject(SceneryObject):
    """Base class for interactive scenery objects. Represents discrete,
    mostly decorative or functional structures.

    Examples include buildings (houses, ATC towers, airports),
    lights (streetlights, fairy lights, lamp posts) and city blocks.

    Compared to LargeSceneryObjects, they are relatively small,
    and interactable/collideable, and may be spawned in groups."""

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.parts: list[BuildingPart] = []

class LargeSceneryObject(SceneryObject):
    """Represents large, static elements forming the base world. Includes
    terrain and oceans. They typically cover large areas, are immovable,
    and can affect core gameplay, e.g. terrain height or GPWSs."""

    def __init__(self, x, y, z):
        super().__init__(x, y, z)

    def draw(self):
        raise NotImplementedError

class CelestialObject(SceneryObject):
    """Reserved for objects that are so far away that
    their position virtually does not change in the sky
    based on location, such as the sun and moon."""

    def __init__(self, image_surface: Surface, direction: pg.Vector3, scale: float = 1.0):
        super().__init__(0, 0, 0)
        self.direction = pg.Vector3(0, 0, -1) if direction.length() < C.EPSILON else direction.normalize()  # guard against zero length
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

        # Save state
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

        # Restore state
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glDepthMask(was_depth_mask_enabled)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA) # Restore default blend func
        if not was_blend_enabled:
            gl.glDisable(gl.GL_BLEND)

        gl.glPopMatrix()
