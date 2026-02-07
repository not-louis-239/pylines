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


from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

import pygame as pg

from pylines.core.custom_types import Colour, RealNumber, Surface
from pylines.objects.scenery.bases import SmallSceneryObject

from .building_parts import generate_building_part_vertices

if TYPE_CHECKING:
    from .building_parts import BuildingPart


class Building(SmallSceneryObject):
    def __init__(self, x: float, y: float, z: float, parts: list[BuildingPart], type_: str):
        super().__init__(x, y, z)
        self.parts = parts
        self.type_ = type_

    def get_vertices(self) -> list[float]:
        all_vertices: list[float] = []
        for part in self.parts:
            all_vertices.extend(generate_building_part_vertices(self.pos, part))
        return all_vertices

    def __repr__(self) -> str:
        x, y, z = self.pos
        return f"Building( pos = ({x}, {y}, {z}), parts = {self.parts} )"

class BuildingDefinition:
    def __init__(
            self,
            parts: list[BuildingPart],
            appearance: BuildingMapAppearance,
            common_name: str
        ) -> None:
        self.parts = parts
        self.appearance = appearance
        self.common_name = common_name

class BuildingMapIconType(Enum):
    SQUARE = auto()
    CIRCLE = auto()
    POINT = auto()

BUILDING_ICON_CORRESPONDENCE: dict[str, BuildingMapIconType] = {
    "square": BuildingMapIconType.SQUARE,
    "circle": BuildingMapIconType.CIRCLE,
    "point": BuildingMapIconType.POINT
}

@dataclass
class BuildingMapAppearance:
    """A purely data storage class that defines how a building will appear
    in the in-game map viewer."""
    colour: Colour
    icon: BuildingMapIconType
    dims: tuple[()] | tuple[int] | tuple[int, int]

def match_building_icon(s: str) -> BuildingMapIconType:
    if s not in BUILDING_ICON_CORRESPONDENCE.keys():
        raise RuntimeError(f"Building icon missing correspondence: '{s}'")

    return BUILDING_ICON_CORRESPONDENCE[s]

def draw_building_icon(surface: Surface, x: RealNumber, y: RealNumber, appearance: BuildingMapAppearance, viewport_zoom: RealNumber = 1):
    if appearance.icon == BuildingMapIconType.CIRCLE:
        if len(appearance.dims) != 1:
            raise ValueError(f"Invalid dimensions: {appearance.dims} for icon type {appearance.icon}. Expected (radius,).")

        radius = appearance.dims[0]
        pg.draw.circle(surface, appearance.colour, (int(x), int(y)), radius / viewport_zoom)

    elif appearance.icon == BuildingMapIconType.SQUARE:
        if len(appearance.dims) != 2:
            raise ValueError(f"Invalid dimensions: {appearance.dims} for icon type {appearance.icon}. Expected (width, height).")

        icon_w, icon_h = appearance.dims

        # Rectangles are drawn from the top-left corner, but we want to center them.
        top_left_x = int(x - icon_w / viewport_zoom / 2)
        top_left_y = int(y - icon_h / viewport_zoom / 2)
        pg.draw.rect(surface, appearance.colour, (top_left_x, top_left_y, icon_w / viewport_zoom, icon_h / viewport_zoom))

    elif appearance.icon == BuildingMapIconType.POINT:
        if len(appearance.dims):
            raise ValueError(f"Invalid dimensions: {appearance.dims} for icon type {appearance.icon}. Expected ().")

        # Draw a tiny circle to represent the point
        POINT_RADIUS = 2
        pg.draw.circle(surface, appearance.colour, (int(x), int(y)), POINT_RADIUS / viewport_zoom)
