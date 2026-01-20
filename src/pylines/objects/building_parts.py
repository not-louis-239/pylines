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

import pygame as pg
from enum import Enum, auto

from pylines.core.custom_types import Coord3, Colour

import OpenGL.GL as gl
import OpenGL.GLU as glu

class Primitive(Enum):
    CUBOID = auto()
    CYLINDER = auto()
    SPHERE = auto()

def set_material(colour: Colour, emissive: bool):
    """Shader should set colour and emissive flags to prepare to draw a part."""
    material_color = [c / 255.0 for c in colour]

    if emissive:
        # A non-emissive part's ambient properties are set to black so it doesn't
        # get brighter from scene lights, and emission is set to its own colour.
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_EMISSION, material_color)
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE, [0.0, 0.0, 0.0, 1.0])
        return

    # A non-emissive part's ambient properties are set to its base colour,
    # and its emission is set to black so it can't glow on its own.
    gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_EMISSION, [0.0, 0.0, 0.0, 1.0])
    gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE, material_color)

def draw_cuboid(pos: pg.Vector3, l: float, w: float, h: float):
    ...

def draw_cylinder(pos: pg.Vector3, r: float, h: float):
    ...

def draw_sphere(pos: pg.Vector3, r: float):
    ...

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
