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

from typing import TYPE_CHECKING, Literal

import numpy as np

from pylines.core.constants import EPSILON, WORLD_SIZE
from pylines.core.utils import map_value
from pylines.objects.scenery import Building
from pylines.objects.building_parts import BuildingPart, match_primitive

if TYPE_CHECKING:
    from pylines.core.asset_manager import WorldData
    from pylines.objects.objects import Runway


class Environment:
    """A class to own terrain, structures and buildings."""

    def __init__(
            self,
            world_data: WorldData,
            runways: list[Runway],
            diagonal_split: Literal['AD', 'BC'] = 'AD',
        ) -> None:

        self.diagonal_split = diagonal_split
        if self.diagonal_split not in ['AD', 'BC']:
            raise ValueError("diagonal_split must be either 'AD' or 'BC'")

        self.height_array: np.ndarray = world_data.height_array

        self.min_h = world_data.MIN_H
        self.max_h = world_data.MAX_H
        self.sea_level = world_data.SEA_LEVEL
        self.h, self.w = self.height_array.shape

        self.runways = runways

        # Convert raw dict entries to runtime objects
        building_defs_raw = world_data.building_defs
        building_placements_raw = world_data.building_placements

        self.building_defs: dict[str, list[BuildingPart]] = {
            name: [
                BuildingPart(
                    part["offset"],
                    match_primitive(part["primitive"]),
                    tuple(part["dims"]),
                    tuple(part["colour"]),
                    part["emissive"]
                ) for part in part_list['parts']
            ] for name, part_list in building_defs_raw.items()
        }

        self.buildings: list[Building] = [
            Building(
                *tuple(placement["pos"]), self.building_defs[placement["type"]]
            ) for placement in building_placements_raw
        ]

    def _world_to_map(self, x: float, z: float) -> tuple[float, float]:
        # Must map to 0 - w or height or else causes camera to go underground
        # This is because mapping to 0-w/h makes _world_to_map sample exactly
        # from the correct pixel
        image_x = map_value(x, -WORLD_SIZE, WORLD_SIZE, 0, self.w)
        image_z = map_value(z, -WORLD_SIZE, WORLD_SIZE, 0, self.h)
        return image_x, image_z

    def height_at(self, x: float, z: float) -> float:
        """Returns the height at world coordinates x and z, in metres."""

        ix, iz = self._world_to_map(x, z)
        ix = np.clip(ix, 0, self.w - (1+EPSILON))
        iz = np.clip(iz, 0, self.h - (1+EPSILON))

        x1, y1 = int(ix), int(iz)
        x2, y2 = x1 + 1, y1 + 1

        fx, fy = ix - x1, iz - y1

        h00 = self.height_array[y1, x1] # A
        h10 = self.height_array[y1, x2] # B
        h01 = self.height_array[y2, x1] # C
        h11 = self.height_array[y2, x2] # D

        if self.diagonal_split == 'AD':
            # Diagonal AD splits the quad into triangles ABD and ACD
            if fy < fx:
                # Point is in triangle ABD
                # Vertices A(0,0), B(1,0), D(1,1)
                u = 1 - fx
                v = fx - fy
                w = fy
                interp = u * h00 + v * h10 + w * h11
            else:
                # Point is in triangle ACD
                # Vertices A(0,0), C(0,1), D(1,1)
                u = 1 - fy
                v = fy - fx
                w = fx
                interp = u * h00 + v * h01 + w * h11
        else: # BC diagonal
            # Diagonal BC splits the quad into triangles ABC and BCD
            if 1 - fx > fy:
                # Point is in triangle ABC
                # Vertices A(0,0), B(1,0), C(0,1)
                u = 1 - fx - fy
                v = fx
                w = fy
                interp = u * h00 + v * h10 + w * h01
            else:
                # Point is in triangle BCD
                # Vertices B(1,0), C(0,1), D(1,1)
                u = 1 - fy
                v = 1 - fx
                w = fx + fy - 1
                interp = u * h10 + v * h01 + w * h11

        raw_height = map_value(interp, 0, 65535, self.min_h, self.max_h)
        final_height = raw_height

        return final_height

    def ground_height(self, x: float, z: float):
        """Fancier version of height_at that accounts for sea level"""

        return max(
            self.height_at(x, z),
            self.sea_level
        )