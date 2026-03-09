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

from typing import Literal, TypeAlias

import pygame as pg

from pylines.core.utils import clamp
import pylines.core.constants as C

ScrollDirection: TypeAlias = Literal[-1, 0, 1]

class ScrollPhysics:
    """Basic scroll physics class for making scrollable UI elements
    such as help menus"""

    DEFAULT_SCROLL_ACCEL = C.WN_H * 0.3   # pix/s²
    PAGE_IMPULSE = C.WN_H                 # pix/s
    WHEEL_IMPULSE = C.WN_H * 0.08         # pix/s
    SCROLL_FRICTION = 0.15                # damping factor when there is no input

    MAX_SCROLL_VELOCITY = C.WN_H * 1.2    # pix/s
    MIN_SCROLL_VELOCITY = C.WN_H * 0.002  # min, below this stop

    def __init__(self, surf_height: int | float, viewport_height: int | float) -> None:
        # Displacement
        self.disp = 0
        self._min_disp = 0
        self._max_disp = max(0, surf_height - viewport_height)

        # Velocity & acceleration
        self.vel = 0
        self.scroll_accel = self.DEFAULT_SCROLL_ACCEL

    def reset(self):
        self.disp = 0
        self.vel = 0

    def take_input(self, dt_ms: int, keys: pg.key.ScancodeWrapper, events: list[pg.event.Event]):
        """Process keyboard and mouse input to modify scroll velocity."""
        dt_seconds = dt_ms / 1000
        accel = self.scroll_accel * dt_seconds

        for event in events:
            if event.type == pg.MOUSEWHEEL:
                self.vel -= event.y * self.WHEEL_IMPULSE

        if keys[pg.K_UP]:
            self.vel -= accel
        if keys[pg.K_DOWN]:
            self.vel += accel
        if keys[pg.K_PAGEUP]:
            self.vel -= self.PAGE_IMPULSE
        if keys[pg.K_PAGEDOWN]:
            self.vel += self.PAGE_IMPULSE

    def update(self, dt_ms: int) -> None:
        # Using Euler integration as perfect physics isn't important for
        # scrollable menus

        dt_seconds = dt_ms / 1000

        self.disp += self.vel * dt_seconds

        # Apply friction
        self.vel *= (1 - self.SCROLL_FRICTION) ** dt_seconds
        if abs(self.vel) < self.MIN_SCROLL_VELOCITY:
            self.vel = 0

        # Clamp displacement to limits
        if self.disp < self._min_disp:
            self.disp = self._min_disp
            self.vel = 0.0
        elif self.disp > self._max_disp:
            self.disp = self._max_disp
            self.vel = 0.0
