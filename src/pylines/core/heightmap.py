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

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import numpy as np
from .utils import map_value
from .constants import EPSILON, WORLD_SIZE

if TYPE_CHECKING:
    from .asset_manager import MapData

class Heightmap:
    def __init__(self, map_data: MapData, diagonal_split: Literal['AD', 'BC'] = 'AD') -> None:
        self.height_array: np.ndarray = map_data.height_array
        self.noise_array: np.ndarray = map_data.noise_array

        self.min_h = map_data.MIN_H
        self.max_h = map_data.MAX_H
        self.sea_level = map_data.SEA_LEVEL
        self.diagonal_split = diagonal_split

        if self.diagonal_split not in ['AD', 'BC']:
            raise ValueError("diagonal_split must be either 'AD' or 'BC'")

        self.h, self.w = self.height_array.shape
        self.max_val = np.max(self.height_array)

        if self.max_val <= 0:
            raise ValueError("Heightmap is empty or invalid")

    def _world_to_map(self, x: float, z: float) -> tuple[float, float]:
        # Must map to 0 - w or height or else causes camera to go underground
        # This is because mapping to 0-w/h makes _world_to_map sample exactly
        # from the correct pixel
        image_x = map_value(x, -WORLD_SIZE, WORLD_SIZE, 0, self.w)
        image_z = map_value(z, -WORLD_SIZE, WORLD_SIZE, 0, self.h)
        return image_x, image_z

    def height_at(self, x: float, z: float, add_tex_noise: bool = False) -> float:
        # Noise only should be used to affect texture, not physical height

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

        final_value = map_value(interp, 0, self.max_val, self.min_h, self.max_h)

        if add_tex_noise:
            # Doesn't need triangle interpolation as it only affects
            # textures, not physics. If height_at is called with
            # add_tex_noise enabled, it is not supposed to be used
            # for physical height, only visual effects such as
            # altitude-based textures.

            noise_ix, noise_iz = self._world_to_map(x, z)
            noise_ix = np.clip(noise_ix, 0, self.w - (1 + EPSILON))
            noise_iz = np.clip(noise_iz, 0, self.h - (1 + EPSILON))

            noise_x1, noise_y1 = int(noise_ix), int(noise_iz)
            noise_x2, noise_y2 = noise_x1 + 1, noise_y1 + 1

            noise_fx, noise_fy = noise_ix - noise_x1, noise_iz - noise_y1

            n00 = self.noise_array[noise_y1, noise_x1]
            n10 = self.noise_array[noise_y1, noise_x2]
            n01 = self.noise_array[noise_y2, noise_x1]
            n11 = self.noise_array[noise_y2, noise_x2]

            # Bilinear interpolation
            interp_noise = (n00 * (1 - noise_fx) * (1 - noise_fy) +
                            n10 * noise_fx * (1 - noise_fy) +
                            n01 * (1 - noise_fx) * noise_fy +
                            n11 * noise_fx * noise_fy)

            # The noise is mapped from [0, 65535] for a 16-bit image, to [-1, 1]
            final_value += map_value(interp_noise, 0, 65535, -1, 1)

        return final_value
