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


import random
from math import cos, pi
from pylines.core.custom_types import Surface

class MenuImageManager:
    def __init__(self, images: list[Surface], change_interval: int = 8) -> None:
        if not images:
            raise ValueError("MenuImageManager requires at least one image to display")

        self.images = images
        self.change_interval = change_interval

        self.time_since_changed: float = 0
        self.active_idx: int = 0  # Must be initialised in __init__ to ensure select_img doesn't raise NameError

        self.pan_start_u: float = 0.0
        self.pan_start_v: float = 0.0
        self.pan_end_u: float = 0.0
        self.pan_end_v: float = 0.0
        self.pan_duration: float = self.change_interval * 0.8

        self.refresh_img()
        self._refresh_pan()

    def refresh_img(self) -> None:
        num_images = len(self.images)

        # Pick a new pan direction

        # Only one image -> no shuffling can occur
        # This guards against an infinite loop
        if num_images == 1:
            self.active_idx = 0
            return

        # Pick an offset between 1 and n-1, then add to current index
        # This guarantees a different index in exactly one calculation
        offset = random.randint(1, num_images - 1)
        self.active_idx = (self.active_idx + offset) % num_images
        self._refresh_pan()

    def _refresh_pan(self) -> None:
        self.pan_start_u = random.random()
        self.pan_start_v = random.random()
        self.pan_end_u = random.random()
        self.pan_end_v = random.random()

    def update(self, dt: int) -> None:
        # Assumes dt is in milliseconds
        dt_seconds = dt / 1000
        self.time_since_changed += dt_seconds

        if self.time_since_changed > self.change_interval:
            self.time_since_changed = 0
            self.refresh_img()

    def draw_current(self, surface: Surface) -> None:
        # Blit the currently selected image to the screen
        image = self.images[self.active_idx]
        image_w, image_h = image.get_size()
        surface_w, surface_h = surface.get_size()

        max_offset_x = max(0, image_w - surface_w)
        max_offset_y = max(0, image_h - surface_h)

        if max_offset_x or max_offset_y:
            t = min(self.time_since_changed / self.pan_duration, 1.0)
            ease = 0.5 - 0.5 * cos(pi * t)

            offset_u = self.pan_start_u + (self.pan_end_u - self.pan_start_u) * ease
            offset_v = self.pan_start_v + (self.pan_end_v - self.pan_start_v) * ease

            offset_x = int(offset_u * max_offset_x)
            offset_y = int(offset_v * max_offset_y)
            surface.blit(image, (-offset_x, -offset_y))
        else:
            surface.blit(image, (0, 0))
