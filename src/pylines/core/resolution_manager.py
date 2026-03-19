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
from typing import Iterable
from OpenGL import GL as gl, GLU as glu

import pygame as pg


@dataclass
class ResolutionState:
    windowed_size: tuple[int, int]
    is_fullscreen: bool

class ViewportManager:
    def __init__(
        self, *, initial_windowed_size: tuple[int, int],
        windowed_flags: int, fullscreen_flags: int,
        supports_auto_resize: bool,
        fov: float, inner_render_limit: float, outer_render_limit: float,
    ) -> None:
        self.state = ResolutionState(windowed_size=initial_windowed_size, is_fullscreen=False)
        self.windowed_flags = windowed_flags
        self.fullscreen_flags = fullscreen_flags
        self.supports_auto_resize = supports_auto_resize
        self.fov = fov
        self.inner_render_limit = inner_render_limit
        self.outer_render_limit = outer_render_limit

    def create_window(self) -> pg.Surface:
        return pg.display.set_mode(self.state.windowed_size, self.windowed_flags)

    def update_gl_viewport(self, size: tuple[int, int]) -> None:
        width, height = size
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(self.fov, width / height, self.inner_render_limit, self.outer_render_limit)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

    def toggle_fullscreen(self, wn: pg.Surface) -> pg.Surface:
        if self.state.is_fullscreen:
            wn = pg.display.set_mode(self.state.windowed_size, self.windowed_flags)
            self.state.is_fullscreen = False
            self.update_gl_viewport(pg.display.get_window_size())
            return wn

        self.state.windowed_size = pg.display.get_window_size()
        desktop_sizes = pg.display.get_desktop_sizes()
        fullscreen_size = desktop_sizes[0] if desktop_sizes else self.state.windowed_size
        wn = pg.display.set_mode(fullscreen_size, self.fullscreen_flags)
        self.state.is_fullscreen = True
        self.update_gl_viewport(fullscreen_size)
        return wn

    def apply_windowed_resize(self, wn: pg.Surface, size: tuple[int, int]) -> pg.Surface:
        if not self.supports_auto_resize:
            wn = pg.display.set_mode(size, self.windowed_flags)
        self.update_gl_viewport(size)
        return wn

    def handle_window_resize_event(
        self, wn: pg.Surface, event: pg.event.Event,
        window_resized_events: Iterable[int],
    ) -> pg.Surface:
        if self.state.is_fullscreen:
            return wn

        if event.type == pg.VIDEORESIZE:
            self.state.windowed_size = event.size
            return self.apply_windowed_resize(wn, self.state.windowed_size)

        if window_resized_events and event.type in window_resized_events:
            self.state.windowed_size = pg.display.get_window_size()
            return self.apply_windowed_resize(wn, self.state.windowed_size)

        return wn
