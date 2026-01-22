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
import math
from math import cos, sin
from typing import TYPE_CHECKING

import numpy as np
import pygame as pg
from OpenGL import GL as gl
from OpenGL import GLU as glu

import pylines.core.constants as C
from pylines.core.custom_types import Coord3, Surface
from pylines.core.time_manager import brightness_from_hour, fetch_hour
from pylines.objects.building_parts import BuildingPart, draw_building_part
from pylines.objects.objects import Entity
from pylines.shaders.shader_manager import load_shader_script

if TYPE_CHECKING:
    from pylines.game.environment import Environment

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

    def draw(self):
        for part in self.parts:
            draw_building_part(self.pos, part)

class LargeSceneryObject(SceneryObject):
    """Represents large, static elements forming the base world. Includes
    terrain and oceans. They typically cover large areas, are immovable,
    and can affect core gameplay, e.g. terrain height or GPWSs."""

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.vertices: list[Coord3] | np.ndarray = [
            (-C.WORLD_SIZE, 0, -C.WORLD_SIZE),
            (-C.WORLD_SIZE, 0, C.WORLD_SIZE),
            (C.WORLD_SIZE, 0, -C.WORLD_SIZE),
            (C.WORLD_SIZE, 0, C.WORLD_SIZE)
        ]

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

class Ground(LargeSceneryObject):
    def __init__(self, textures: dict[str, Surface], env: Environment) -> None:
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
        step = C.WORLD_SIZE * 2 / res
        texture_scale = 200.0 / (C.WORLD_SIZE * 2)

        def vert_index(r: int, c: int) -> int:
            return r * (res + 1) + c

        # ---- vertices ----
        for r in range(res + 1):
            for c in range(res + 1):
                x = -C.WORLD_SIZE + c * step
                z = -C.WORLD_SIZE + r * step
                y = self.env.height_at(x, z)

                u = (x + C.WORLD_SIZE) * texture_scale
                v = (z + C.WORLD_SIZE) * texture_scale

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

class Ocean(LargeSceneryObject):
    def __init__(self, image_surface: Surface, env: "Environment") -> None:
        super().__init__(0, env.sea_level, 0)
        self.texture_id = self._load_texture(image_surface)
        self.env = env
        self.grid_resolution = 400  # Must match Ground for now
        self.texture_repeat_count = 25.0

        self.shader = load_shader_script(
            "src/pylines/shaders/ocean.vert",
            "src/pylines/shaders/ocean.frag"
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
        step = C.WORLD_SIZE * 2 / res
        texture_scale = self.texture_repeat_count / (C.WORLD_SIZE * 2)

        def vert_index(r: int, c: int) -> int:
            return r * (res + 1) + c

        # ---- vertices ----
        for r in range(res + 1):
            for c in range(res + 1):
                x = -C.WORLD_SIZE + c * step
                z = -C.WORLD_SIZE + r * step
                y = self.env.sea_level
                terrain_y = self.env.height_at(x, z)

                u = (x + C.WORLD_SIZE) * texture_scale
                v = (z + C.WORLD_SIZE) * texture_scale

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

    def draw(self):
        brightness = brightness_from_hour(fetch_hour())

        gl.glPushMatrix()

        was_blend_enabled = gl.glIsEnabled(gl.GL_BLEND)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDepthMask(gl.GL_FALSE)  # Don't write to depth buffer

        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(1.0, 1.0)

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

# TODO: Add stars
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

class Building(SmallSceneryObject):
    def __init__(self, x: float, y: float, z: float, parts: list[BuildingPart]):
        super().__init__(x, y, z)
        self.parts = parts

    def draw(self):
        for part in self.parts:
            draw_building_part(self.pos, part)

    def __repr__(self) -> str:
        x, y, z = self.pos
        return f"Building( pos = ({x}, {y}, {z}), parts = {self.parts} )"
