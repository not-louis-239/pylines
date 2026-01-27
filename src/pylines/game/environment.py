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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import math
import numpy as np
import random
import pygame as pg

from pylines.core.constants import EPSILON, HALF_WORLD_SIZE
from pylines.core.custom_types import Coord2
from pylines.core.asset_manager import Images
from pylines.core.utils import map_value
from pylines.objects.building_parts import BuildingPart, match_primitive
from pylines.objects.buildings import (
    Building,
    BuildingDefinition,
    BuildingMapAppearance,
    match_building_icon,
)
from pylines.objects.scenery.runway import Runway
from pylines.objects.scenery.sky import Star, CloudLayer

if TYPE_CHECKING:
    from pylines.core.asset_manager import WorldData, Fonts


@dataclass
class ProhibitedZoneData:
    code: str
    name: str
    pos: Coord2
    dims: Coord2

class Environment:
    """A class to own and store terrain, structure and building
    information or runtime objects."""

    def __init__(
            self,
            world_data: WorldData,
            fonts: Fonts,
            images: Images,
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

        # Convert runway JSON to runway objects
        self.fonts = fonts  # Used for runway text
        self.images = images
        self.runways: list[Runway] = [
            Runway(
                runway["name"],
                runway["pos"][0],
                runway["pos"][1],
                runway["pos"][2],
                runway["width"],
                runway["length"],
                runway["heading"],
                self.fonts,
                self.images.base_runway_texture
            ) for runway in world_data.runway_data
        ]

        # Convert raw dict entries to runtime objects
        self.building_defs: dict[str, BuildingDefinition] = {
            name: BuildingDefinition(
                parts=[
                    BuildingPart(
                        part["offset"],
                        match_primitive(part["primitive"]),
                        tuple(part["dims"]),
                        tuple(part["colour"]),
                        part["emissive"]
                    ) for part in info['parts']
                ],
                appearance=BuildingMapAppearance(
                    tuple(info["map_appearance"]["colour"]),
                    match_building_icon(info["map_appearance"]["icon"]),
                    tuple(info["map_appearance"]["dims"])
                )
            )
            for name, info in world_data.building_defs.items()
        }

        try:
            self.buildings: list[Building] = [
                Building(
                    placement["pos"][0],
                    placement["pos"][1],
                    placement["pos"][2],
                    self.building_defs[placement["type"]].parts,
                    placement["type"]
                ) for placement in world_data.building_placements
            ]
        except KeyError as e:
            offender = str(e).strip("'")
            raise RuntimeError(f"Building definition missing for type: '{offender}'")

        # Prohibited zones
        self.prohibited_zones = [
            ProhibitedZoneData(
                zone["code"],
                zone["name"],
                tuple(zone["pos"]),
                tuple(zone["dims"])
            ) for zone in world_data.prohibited_zones
        ]

        # Stars
        starfield_data_raw = world_data.starfield_data
        starfield_seed = starfield_data_raw["seed"]
        num_stars = starfield_data_raw["count"]

        star_rng = random.Random(starfield_seed)
        self.stars: list[Star] = []
        for _ in range(num_stars):
            u = star_rng.uniform(-1, 1)
            azimuth = star_rng.uniform(0, math.pi * 2)
            elevation = math.asin(u)

            x = math.cos(elevation) * math.cos(azimuth)
            y = math.sin(elevation)
            z = math.cos(elevation) * math.sin(azimuth)

            direction = pg.Vector3(x, y, z)

            brightness = 10 ** star_rng.uniform(-1.5, 0.35)
            size = (0.7 + 1.6 * brightness ** 0.4) * star_rng.uniform(0.9, 1.1)
            colour = (255, 255, 255) if brightness < 3 else star_rng.choice(
                [(255, 217, 217), (255, 239, 214), (255, 251, 217), (199, 231, 255)]
            )

            self.stars.append(Star(direction, brightness, colour, size))

        # Cloud layers
        self.cloud_layers = [
            CloudLayer(
                cloud_layer["altitude"],
                cloud_layer["thickness"],
                cloud_layer["coverage"],
                cloud_layer["seed"],
                images.cloud_blob
            ) for cloud_layer in world_data.cloud_layers
        ]

    def _world_to_map(self, x: float, z: float) -> tuple[float, float]:
        # Must map to 0 - w or height or else causes camera to go underground
        # This is because mapping to 0-w/h makes _world_to_map sample exactly
        # from the correct pixel
        image_x = map_value(x, -HALF_WORLD_SIZE, HALF_WORLD_SIZE, 0, self.w)
        image_z = map_value(z, -HALF_WORLD_SIZE, HALF_WORLD_SIZE, 0, self.h)
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
