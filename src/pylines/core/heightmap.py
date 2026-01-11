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

import numpy as np
from .utils import map_value
from .constants import WORLD_SIZE, EPSILON

class Heightmap:
    def __init__(self, height_array: np.ndarray, min_h: float, max_h: float, world_size: float) -> None:
        self.h_array = height_array
        self.min_h = min_h
        self.max_h = max_h
        self.world_size = world_size

        self.h, self.w = height_array.shape
        self.max_val = np.max(height_array)

        if self.max_val <= 0:
            raise ValueError("Heightmap is empty or invalid")

    def _world_to_map(self, x: float, z: float) -> tuple[float, float]:
        image_x = map_value(x, -self.world_size, self.world_size, 0, self.w - 1)
        image_z = map_value(z, -self.world_size, self.world_size, 0, self.h - 1)
        return image_x, image_z

    def height_at(self, x: float, z: float) -> float:
        ix, iz = self._world_to_map(x, z)

        ix = np.clip(ix, 0, self.w - (1+EPSILON))
        iz = np.clip(iz, 0, self.h - (1+EPSILON))

        x1, y1 = int(ix), int(iz)
        x2, y2 = x1 + 1, y1 + 1

        fx, fy = ix - x1, iz - y1

        h00 = self.h_array[y1, x1]
        h10 = self.h_array[y1, x2]
        h01 = self.h_array[y2, x1]
        h11 = self.h_array[y2, x2]

        interp = (
            h00 * (1 - fx) * (1 - fy) +
            h10 * fx * (1 - fy) +
            h01 * (1 - fx) * fy +
            h11 * fx * fy
        )

        return map_value(interp, 0, self.max_val, self.min_h, self.max_h)
