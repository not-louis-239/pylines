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

import random
from typing import TYPE_CHECKING

import pygame as pg

import pylines.core.constants as C
from pylines.core.custom_types import RealNumber, Surface

if TYPE_CHECKING:
    from pylines.core.asset_manager import Images

BASE_SMOKE_RISE_SPEED = 200  # pixels per second
BASE_SMOKE_BLOB_SIZE = 300  # pixels, diameter of the smoke blob when spawned. Will be scaled randomly by each blob, but this is the base size.
SMOKE_DRIFT_FACTOR = 10
SMOKE_DENSITY_FACTOR = 15  # number of new smoke blobs per second

class SmokeBlob:
    def __init__(self, x: RealNumber, y: RealNumber) -> None:
        self.screen_pos: pg.Vector2 = pg.Vector2(x, y)
        self.speed = random.uniform(0.7, 1.3) * BASE_SMOKE_RISE_SPEED
        self.diameter: float = random.uniform(0.6, 1.5) * BASE_SMOKE_BLOB_SIZE

    def update(self, dt: int) -> None:
        self.screen_pos.y -= self.speed * dt/1000  # move up screen
        self.screen_pos.x += random.uniform(-1, 1) * SMOKE_DRIFT_FACTOR * dt/1000

class SmokeManager:
    """Dedicated object for managing smoke effects during the crash overlay"""

    def __init__(self, images: Images) -> None:
        self.smoke_blobs: list[SmokeBlob] = []
        self.images = images  # SmokeManager needs a reference to the images to draw the smoke blobs

        # Cache smoke blob sizes to avoid scaling per-frame, which is wasteful
        self.smoke_blob_cache: dict[int, Surface] = {}
        self.smoke_blob_cache_min = max(1, int(BASE_SMOKE_BLOB_SIZE * 0.6))
        self.smoke_blob_cache_max = max(self.smoke_blob_cache_min, int(BASE_SMOKE_BLOB_SIZE * 1.5))
        for size in range(self.smoke_blob_cache_min, self.smoke_blob_cache_max + 1):
            scaled = pg.transform.scale(self.images.smoke_blob, (size, size))
            premultiplied = scaled.copy()
            rgb = pg.surfarray.pixels3d(premultiplied)
            alpha = pg.surfarray.pixels_alpha(premultiplied)
            rgb[:] = (rgb * (alpha[..., None] / 255.0)).astype(rgb.dtype)
            del rgb
            del alpha
            self.smoke_blob_cache[size] = premultiplied

    def spawn_smoke_blob(self) -> None:
        safety = BASE_SMOKE_BLOB_SIZE * 1.5  # visual buffer
        new = SmokeBlob(random.uniform(-safety, C.WN_W + safety), C.WN_H + safety)
        self.smoke_blobs.append(new)

    def update(self, dt: int) -> None:
        for blob in self.smoke_blobs:
            blob.update(dt)

        safety = BASE_SMOKE_BLOB_SIZE * 1.5  # visual buffer, again

        # Cull off-screen blobs
        self.smoke_blobs = [
            blob for blob in self.smoke_blobs
            if blob.screen_pos.y + blob.diameter > -safety
        ]

        spawn_rate = SMOKE_DENSITY_FACTOR * dt/1000  # number of smoke blobs, avg.
        spawn_count = int(spawn_rate)  # number of guaranteed spawns

        # Spawn guaranteed smoke blobs
        for _ in range(spawn_count):
            self.spawn_smoke_blob()

        # Fraction of a blob -> probability of an extra smoke blob
        if random.random() < (spawn_rate - spawn_count):
            self.spawn_smoke_blob()

    def draw_smoke_blobs(self, surface: Surface) -> None:
        for blob in self.smoke_blobs:
            size = int(blob.diameter)
            cached_surf: Surface | None = self.smoke_blob_cache.get(size)

            if cached_surf is None:
                raise IndexError(
                    "Smoke blob size out of cache range: "
                    f"requested={size}, cached_range={self.smoke_blob_cache_min}-{self.smoke_blob_cache_max}"
                )

            surface.blit(
                cached_surf,
                (int(blob.screen_pos.x - size/2), int(blob.screen_pos.y - size/2)),
                special_flags=pg.BLEND_PREMULTIPLIED,
            )
