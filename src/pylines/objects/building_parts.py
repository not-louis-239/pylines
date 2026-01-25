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
and generate their vertex data for batched rendering.
"""

from enum import Enum, auto
import math
import numpy as np
import pygame as pg

from pylines.core.custom_types import Colour, Coord3
from pylines.core.time_manager import brightness_from_hour, fetch_hour


class Primitive(Enum):
    CUBOID = auto()
    CYLINDER = auto()
    SPHERE = auto()

PRIMITIVE_CORRESPONDENCE: dict[str, Primitive] = {
    "cuboid": Primitive.CUBOID,
    "cylinder": Primitive.CYLINDER,
    "sphere": Primitive.SPHERE
}

def match_primitive(s: str) -> Primitive:
    if s not in PRIMITIVE_CORRESPONDENCE.keys():
        raise RuntimeError(f"Primitive missing correspondence: '{s}'")

    return PRIMITIVE_CORRESPONDENCE[s]

def get_part_colour(colour: Colour) -> tuple[float, float, float]:
    """Calculates the final color of a part based on its base color."""
    r, g, b = colour
    return r / 255.0, g / 255.0, b / 255.0

def generate_cuboid_vertices(pos: pg.Vector3, l: float, h: float, w: float, color: tuple[float, float, float], emissive: float) -> list[float]:
    """Generates vertices for a cuboid, including position, color, and normal."""
    hl, hw, hh = l / 2, w / 2, h / 2

    vertices_pos = [
        (pos.x - hl, pos.y - hh, pos.z + hw),  # 0
        (pos.x + hl, pos.y - hh, pos.z + hw),  # 1
        (pos.x + hl, pos.y + hh, pos.z + hw),  # 2
        (pos.x - hl, pos.y + hh, pos.z + hw),  # 3
        (pos.x - hl, pos.y - hh, pos.z - hw),  # 4
        (pos.x + hl, pos.y - hh, pos.z - hw),  # 5
        (pos.x + hl, pos.y + hh, pos.z - hw),  # 6
        (pos.x - hl, pos.y + hh, pos.z - hw),  # 7
    ]

    faces = [
        (0, 1, 2, 3),
        (1, 5, 6, 2),
        (5, 4, 7, 6),
        (4, 0, 3, 7),
        (3, 2, 6, 7),
        (4, 5, 1, 0),
    ]

    normals = [
        (0, 0, 1),
        (1, 0, 0),
        (0, 0, -1),
        (-1, 0, 0),
        (0, 1, 0),
        (0, -1, 0),
    ]

    vertex_data: list[float] = []

    for normal, (i0, i1, i2, i3) in zip(normals, faces):
        # quad → two triangles: (0,1,2) and (0,2,3)
        for idx in (i0, i1, i2, i0, i2, i3):
            vertex_data.extend([
                *vertices_pos[idx],
                *color,
                *normal,
                emissive,
            ])

    return vertex_data

def generate_cylinder_vertices(pos: pg.Vector3, r: float, h: float, color: tuple[float, float, float], emissive: float, segments: int = 32) -> list[float]:
    """Generates vertices for a cylinder, including position, color, and normal."""
    vertex_data = []
    angle_step = 2 * math.pi / segments
    half_h = h / 2

    # Body
    for i in range(segments):
        angle1 = i * angle_step
        angle2 = (i + 1) * angle_step

        x1, z1 = r * math.cos(angle1), r * math.sin(angle1)
        x2, z2 = r * math.cos(angle2), r * math.sin(angle2)

        p1_top = (pos.x + x1, pos.y + half_h, pos.z + z1)
        p1_bot = (pos.x + x1, pos.y - half_h, pos.z + z1)
        p2_top = (pos.x + x2, pos.y + half_h, pos.z + z2)
        p2_bot = (pos.x + x2, pos.y - half_h, pos.z + z2)

        normal1 = (x1 / r, 0, z1 / r)
        normal2 = (x2 / r, 0, z2 / r)

        # Triangle 1
        vertex_data.extend([*p1_bot, *color, *normal1, emissive])
        vertex_data.extend([*p2_bot, *color, *normal2, emissive])
        vertex_data.extend([*p1_top, *color, *normal1, emissive])

        # Triangle 2
        vertex_data.extend([*p1_top, *color, *normal1, emissive])
        vertex_data.extend([*p2_bot, *color, *normal2, emissive])
        vertex_data.extend([*p2_top, *color, *normal2, emissive])

    # Top Cap
    top_center = (pos.x, pos.y + half_h, pos.z)
    normal_top = (0, 1, 0)
    for i in range(segments):
        angle1 = i * angle_step
        angle2 = (i + 1) * angle_step

        x1, z1 = r * math.cos(angle1), r * math.sin(angle1)
        x2, z2 = r * math.cos(angle2), r * math.sin(angle2)

        p1 = (pos.x + x1, pos.y + half_h, pos.z + z1)
        p2 = (pos.x + x2, pos.y + half_h, pos.z + z2)

        vertex_data.extend([*top_center, *color, *normal_top, emissive])
        vertex_data.extend([*p1, *color, *normal_top, emissive])
        vertex_data.extend([*p2, *color, *normal_top, emissive])

    # Bottom Cap
    bot_center = (pos.x, pos.y - half_h, pos.z)
    normal_bot = (0, -1, 0)
    for i in range(segments):
        angle1 = i * angle_step
        angle2 = (i + 1) * angle_step

        x1, z1 = r * math.cos(angle1), r * math.sin(angle1)
        x2, z2 = r * math.cos(angle2), r * math.sin(angle2)

        p1 = (pos.x + x1, pos.y - half_h, pos.z + z1)
        p2 = (pos.x + x2, pos.y - half_h, pos.z + z2)

        vertex_data.extend([*bot_center, *color, *normal_bot, emissive])
        vertex_data.extend([*p2, *color, *normal_bot, emissive])
        vertex_data.extend([*p1, *color, *normal_bot, emissive])

    return vertex_data

def generate_sphere_vertices(pos: pg.Vector3, r: float, color: tuple[float, float, float], emissive: float, stacks: int = 16, sectors: int = 32) -> list[float]:
    """Generates vertices for a sphere, including position, color, and normal."""
    vertex_data = []
    stack_step = math.pi / stacks
    sector_step = 2 * math.pi / sectors

    for i in range(stacks):
        stack_angle1 = i * stack_step
        stack_angle2 = (i + 1) * stack_step

        for j in range(sectors):
            sector_angle1 = j * sector_step
            sector_angle2 = (j + 1) * sector_step

            # Vertices of the quad
            p1 = (
                pos.x + r * math.sin(stack_angle1) * math.cos(sector_angle1),
                pos.y + r * math.cos(stack_angle1),
                pos.z + r * math.sin(stack_angle1) * math.sin(sector_angle1),
            )
            p2 = (
                pos.x + r * math.sin(stack_angle1) * math.cos(sector_angle2),
                pos.y + r * math.cos(stack_angle1),
                pos.z + r * math.sin(stack_angle1) * math.sin(sector_angle2),
            )
            p3 = (
                pos.x + r * math.sin(stack_angle2) * math.cos(sector_angle1),
                pos.y + r * math.cos(stack_angle2),
                pos.z + r * math.sin(stack_angle2) * math.sin(sector_angle1),
            )
            p4 = (
                pos.x + r * math.sin(stack_angle2) * math.cos(sector_angle2),
                pos.y + r * math.cos(stack_angle2),
                pos.z + r * math.sin(stack_angle2) * math.sin(sector_angle2),
            )

            # Normals are just the normalized position vectors from the center
            n1 = tuple(c / r for c in (p1[0]-pos.x, p1[1]-pos.y, p1[2]-pos.z))
            n2 = tuple(c / r for c in (p2[0]-pos.x, p2[1]-pos.y, p2[2]-pos.z))
            n3 = tuple(c / r for c in (p3[0]-pos.x, p3[1]-pos.y, p3[2]-pos.z))
            n4 = tuple(c / r for c in (p4[0]-pos.x, p4[1]-pos.y, p4[2]-pos.z))

            # Triangle 1
            vertex_data.extend([*p1, *color, *n1, emissive])
            vertex_data.extend([*p3, *color, *n3, emissive])
            vertex_data.extend([*p2, *color, *n2, emissive])

            # Triangle 2
            vertex_data.extend([*p2, *color, *n2, emissive])
            vertex_data.extend([*p3, *color, *n3, emissive])
            vertex_data.extend([*p4, *color, *n4, emissive])

    return vertex_data

def generate_building_part_vertices(world_pos: pg.Vector3, part: "BuildingPart") -> list[float]:
    """Generates all vertices for a single building part."""
    pos = world_pos + part.offset
    color = get_part_colour(part.colour)
    emissive_float = 1.0 if part.emissive else 0.0

    if part.primitive == Primitive.CUBOID:
        l, h, w = part.dims
        return generate_cuboid_vertices(pos, l, h, w, color, emissive_float)
    elif part.primitive == Primitive.CYLINDER:
        r, h = part.dims
        return generate_cylinder_vertices(pos, r, h, color, emissive_float)
    elif part.primitive == Primitive.SPHERE:
        r = part.dims[0]
        return generate_sphere_vertices(pos, r, color, emissive_float)
    else:
        raise ValueError(f"Missing vertices generator for primitive: {part.primitive.value}")

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

    def __repr__(self) -> str:
        ox, oy, oz = self.offset
        prim = self.primitive.value
        dims = self.dims
        col = self.colour
        emissive = self.emissive
        return f"BuildingPart( offset = ({ox}, {oy}, {oz}), primitive = {prim}, dims = {dims}, col = {col}, emissive = {emissive} )"
