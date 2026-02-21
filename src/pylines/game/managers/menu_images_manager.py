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

from pylines.core.custom_types import Surface

class MenuImageManager:
    def __init__(self, images: list[Surface], change_interval: int = 8) -> None:
        if not images:
            raise ValueError("MenuImageManager requires at least one image to display")

        self.images = images
        self.change_interval = change_interval

        self.time_since_changed: float = 0
        self.active_idx: int = 0  # Must be initialised in __init__ to ensure select_img doesn't raise NameError
        self.select_img()

    def select_img(self) -> None:
        num_images = len(self.images)

        # Only one image -> no shuffling can occur
        # This guards against an infinite loop
        if num_images == 1:
            self.active_idx = 0
            return

        # Pick an offset between 1 and n-1, then add to current index
        # This guarantees a different index in exactly one calculation
        offset = random.randint(1, num_images - 1)
        self.active_idx = (self.active_idx + offset) % num_images

    def update(self, dt: int) -> None:
        # Assumes dt is in milliseconds
        dt_seconds = dt / 1000
        self.time_since_changed += dt_seconds

        if self.time_since_changed > self.change_interval:
            self.time_since_changed = 0
            self.select_img()

    def draw_current(self, surface: Surface) -> None:
        # Blit the currently selected image to the screen
        # This blits to the top left of the screen as it assumes
        # that the images are the same size as the screen.
        surface.blit(self.images[self.active_idx], (0, 0))
