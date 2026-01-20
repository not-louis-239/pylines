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

"""
building_parts.py

contains the ingredients to make buildings
and draw them
"""

from enum import Enum, auto

import OpenGL.GL as gl
import OpenGL.GLU as glu
import pygame as pg

from pylines.core.custom_types import Colour, Coord3
from pylines.core.time_manager import brightness_from_hour, fetch_hour


class Primitive(Enum):
    CUBOID = auto()
    CYLINDER = auto()
    SPHERE = auto()

def set_material(colour: Colour, emissive: bool):
    """Shader should set colour and emissive flags to prepare to draw a part."""
    r, g, b = [c / 255.0 for c in colour] # Normalize to 0.0-1.0

    if emissive:
        # If emissive, set the color directly, unaffected by ambient brightness.
        # This color will be used directly for rendering.
        gl.glColor3f(r, g, b)
    else:
        # If not emissive, its color is affected by daylight brightness.
        # Fetch current brightness and apply it to the RGB channels.
        daylight_brightness = brightness_from_hour(fetch_hour())

        adjusted_r = r * daylight_brightness
        adjusted_g = g * daylight_brightness
        adjusted_b = b * daylight_brightness

        gl.glColor3f(adjusted_r, adjusted_g, adjusted_b)

def draw_cuboid(pos: pg.Vector3, l: float, w: float, h: float):
    """Draws a cuboid centered at pos."""
    hl, hw, hh = l / 2, w / 2, h / 2
    vertices = [
        (pos.x - hl, pos.y - hh, pos.z + hw),  # 0: bottom-left-front
        (pos.x + hl, pos.y - hh, pos.z + hw),  # 1: bottom-right-front
        (pos.x + hl, pos.y + hh, pos.z + hw),  # 2: top-right-front
        (pos.x - hl, pos.y + hh, pos.z + hw),  # 3: top-left-front
        (pos.x - hl, pos.y - hh, pos.z - hw),  # 4: bottom-left-back
        (pos.x + hl, pos.y - hh, pos.z - hw),  # 5: bottom-right-back
        (pos.x + hl, pos.y + hh, pos.z - hw),  # 6: top-right-back
        (pos.x - hl, pos.y + hh, pos.z - hw),  # 7: top-left-back
    ]
    faces = [
        (0, 1, 2, 3),  # front
        (1, 5, 6, 2),  # right
        (5, 4, 7, 6),  # back
        (4, 0, 3, 7),  # left
        (3, 2, 6, 7),  # top
        (4, 5, 1, 0),  # bottom
    ]
    normals = [
        (0, 0, 1),   # front
        (1, 0, 0),   # right
        (0, 0, -1),  # back
        (-1, 0, 0),  # left
        (0, 1, 0),   # top
        (0, -1, 0),  # bottom
    ]

    gl.glBegin(gl.GL_QUADS)
    for i, face in enumerate(faces):
        gl.glNormal3fv(normals[i])
        for vertex_index in face:
            gl.glVertex3fv(vertices[vertex_index])
    gl.glEnd()

def draw_cylinder(pos: pg.Vector3, r: float, h: float):
    """Draws a cylinder centered at pos, standing upright on the Y axis."""
    quad = glu.gluNewQuadric()
    glu.gluQuadricNormals(quad, glu.GLU_SMOOTH)

    gl.glPushMatrix()
    gl.glTranslatef(pos.x, pos.y, pos.z)
    gl.glRotatef(-90.0, 1.0, 0.0, 0.0)  # Align Z (glu default) with world Y
    gl.glTranslatef(0, 0, -h / 2)       # Center it vertically

    # Cylinder Body
    glu.gluCylinder(quad, r, r, h, 32, 1)

    # Bottom Cap
    gl.glPushMatrix()
    gl.glRotatef(180, 1, 0, 0) # Flip to face down
    glu.gluDisk(quad, 0, r, 32, 1)
    gl.glPopMatrix()

    # Top Cap
    gl.glPushMatrix()
    gl.glTranslatef(0, 0, h)
    glu.gluDisk(quad, 0, r, 32, 1)
    gl.glPopMatrix()

    gl.glPopMatrix()
    glu.gluDeleteQuadric(quad)

def draw_sphere(pos: pg.Vector3, r: float):
    """Draws a sphere centered at pos."""
    quad = glu.gluNewQuadric()
    glu.gluQuadricNormals(quad, glu.GLU_SMOOTH)

    gl.glPushMatrix()
    gl.glTranslatef(pos.x, pos.y, pos.z)
    glu.gluSphere(quad, r, 32, 32)
    gl.glPopMatrix()

    glu.gluDeleteQuadric(quad)

def draw_building_part(world_pos: pg.Vector3, part: BuildingPart):
    pos = world_pos + part.offset
    set_material(part.colour, part.emissive)

    if part.primitive == Primitive.CUBOID:
        draw_cuboid(pos, *part.dims)
    elif part.primitive == Primitive.CYLINDER:
        draw_cylinder(pos, *part.dims)
    elif part.primitive == Primitive.SPHERE:
        draw_sphere(pos, *part.dims)

class BuildingPart:
    def __init__(
        self, offset: Coord3, primitive: Primitive, dims: tuple[float, ...],
        colour: Colour, emissive: bool = False,
    ) -> None:
        self.offset = pg.Vector3(*offset)
        self.primitive = primitive
        self.dims = dims
        self.colour = colour
        self.emissive = emissive
