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

from pylines.core.custom_types import Coord2
import pylines.core.constants as C

ScrollDirection: TypeAlias = Literal[-1, 0, 1]

class ScrollPhysics1D:
    """Basic scroll physics class for making scrollable UI elements
    such as help menus"""

    DEFAULT_SCROLL_ACCEL = C.WN_H * 0.3   # pix/s²
    PAGE_IMPULSE = C.WN_H                 # pix/s
    WHEEL_IMPULSE = C.WN_H * 0.08         # pix/s
    SCROLL_FRICTION = 0.935                 # damping factor per second when there is no input

    MAX_SCROLL_VELOCITY = C.WN_H * 1.2    # pix/s
    MIN_SCROLL_VELOCITY = C.WN_H * 0.002  # min, below this stop

    def __init__(self, surf_height: int | float, viewport_height: int | float) -> None:
        self.view_height = viewport_height

        # Displacement
        self.disp = 0
        self.min_disp = 0
        self.max_disp = max(0, surf_height - viewport_height)

        # Velocity & acceleration
        self.vel = 0
        self.scroll_accel = self.DEFAULT_SCROLL_ACCEL

    def reset(self):
        self.disp = 0
        self.vel = 0

    def take_input(self, keys: pg.key.ScancodeWrapper, events: list[pg.event.Event], dt_ms: int):
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
        if self.disp < self.min_disp:
            self.disp = self.min_disp
            self.vel = 0.0
        elif self.disp > self.max_disp:
            self.disp = self.max_disp
            self.vel = 0.0

class ScrollPhysics2D:
    """Scroll physics for 2D environments like maps or large canvases."""

    DEFAULT_SCROLL_ACCEL = C.WN_H * 0.3
    PAGE_IMPULSE = C.WN_H
    WHEEL_IMPULSE = C.WN_H * 0.08
    SCROLL_FRICTION = 0.15

    MAX_SCROLL_VELOCITY = C.WN_H * 1.2
    MIN_SCROLL_VELOCITY = C.WN_H * 0.002

    def __init__(self, surf_size: Coord2 | pg.Vector2, viewport_size: Coord2 | pg.Vector2) -> None:
        # Displacement and boundaries
        self.disp = pg.Vector2(0, 0)
        self._disp_topleft = pg.Vector2(0, 0)

        # Calculate max displacement based on surface vs viewport dimensions
        max_x = max(0, surf_size[0] - viewport_size[0])
        max_y = max(0, surf_size[1] - viewport_size[1])
        self._disp_bottomright = pg.Vector2(max_x, max_y)

        # Velocity & acceleration
        self.vel = pg.Vector2(0, 0)
        self.scroll_accel = self.DEFAULT_SCROLL_ACCEL

        # Panning for click-and-drag support
        self.is_panning: bool = False

    def reset(self):
        self.disp.update(0, 0)
        self.vel.update(0, 0)

    def take_input(self, dt_ms: int, keys: pg.key.ScancodeWrapper, events: list[pg.event.Event]):
        """Process keyboard, mouse input and click-and-drag for 2D movement."""
        dt_seconds = dt_ms / 1000
        accel_mag = self.scroll_accel * dt_seconds

        for event in events:
            if event.type == pg.MOUSEWHEEL:
                # Standard wheel affects Y, Shift+Wheel often used for X
                self.vel.y -= event.y * self.WHEEL_IMPULSE
                self.vel.x += event.x * self.WHEEL_IMPULSE

            # Toggle panning state (Middle mouse or Left click)
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1: # Left click
                    self.is_panning = True
                    # Clear relative movement before starting
                    pg.mouse.get_rel()

            if event.type == pg.MOUSEBUTTONUP:
                if event.button == 1:
                    self.is_panning = False

        if self.is_panning:
            # Get mouse movement since last frame
            mouse_rel = pg.Vector2(pg.mouse.get_rel())

            if mouse_rel.length_squared() > 0:
                # Move displacement opposite to mouse direction
                self.disp -= mouse_rel

                # Update velocity so it "flicks" when released
                # Velocity = distance / time
                self.vel = -mouse_rel / dt_seconds
        else:
            # Only process keyboard movement if not dragging
            if keys[pg.K_UP] or keys[pg.K_w]: self.vel.y -= accel_mag
            if keys[pg.K_DOWN] or keys[pg.K_s]: self.vel.y += accel_mag
            if keys[pg.K_LEFT] or keys[pg.K_a]: self.vel.x -= accel_mag
            if keys[pg.K_RIGHT] or keys[pg.K_d]: self.vel.x += accel_mag

        # Page impulses (vertical focus)
        if keys[pg.K_PAGEUP]:
            self.vel.y -= self.PAGE_IMPULSE
        if keys[pg.K_PAGEDOWN]:
            self.vel.y += self.PAGE_IMPULSE

    def update(self, dt_ms: int) -> None:
        dt_seconds = dt_ms / 1000

        # Update displacement
        self.disp += self.vel * dt_seconds

        # Apply friction per axis
        friction_factor = (1 - self.SCROLL_FRICTION) ** dt_seconds
        self.vel *= friction_factor

        # Stop if velocity is near zero
        if self.vel.length_squared() < self.MIN_SCROLL_VELOCITY**2:
            self.vel.update(0, 0)

        # Clamp displacement to boundaries
        self._clamp_displacement()

    def _clamp_displacement(self) -> None:
        """Ensure the displacement stays within boundaries."""
        # X-axis clamping
        if self.disp.x < self._disp_topleft.x:
            self.disp.x = self._disp_topleft.x
            self.vel.x = 0
        elif self.disp.x > self._disp_bottomright.x:
            self.disp.x = self._disp_bottomright.x
            self.vel.x = 0

        # Y-axis clamping
        if self.disp.y < self._disp_topleft.y:
            self.disp.y = self._disp_topleft.y
            self.vel.y = 0
        elif self.disp.y > self._disp_bottomright.y:
            self.disp.y = self._disp_bottomright.y
            self.vel.y = 0