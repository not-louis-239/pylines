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

from typing import TYPE_CHECKING

import pygame as pg

import pylines.core.constants as C
from pylines.core.utils import draw_text, draw_transparent_rect
from pylines.game.managers.pop_up_menus import PopupMenu

if TYPE_CHECKING:
    from pylines.game.game import Game

class DiagnosticsManager(PopupMenu):
    MAX_HISTORY_LEN: int = 100
    DISPLAY_RECT_W: int = 300
    DISPLAY_RECT_H: int = 150
    DISPLAY_RECT_BORDER_W: int = 2

    # Dyamically calculated
    frame_graph_plot_rect = pg.Rect(
        DISPLAY_RECT_BORDER_W, C.WN_H - DISPLAY_RECT_H + DISPLAY_RECT_BORDER_W,
        DISPLAY_RECT_W - 2 * DISPLAY_RECT_BORDER_W, DISPLAY_RECT_H - 2 * DISPLAY_RECT_BORDER_W
    )
    tick_graph_plot_rect = pg.Rect(
        C.WN_W - DISPLAY_RECT_W + DISPLAY_RECT_BORDER_W, C.WN_H - DISPLAY_RECT_H + DISPLAY_RECT_BORDER_W,
        DISPLAY_RECT_W - 2 * DISPLAY_RECT_BORDER_W, DISPLAY_RECT_H - 2 * DISPLAY_RECT_BORDER_W
    )

    def __init__(self, game: Game) -> None:
        super().__init__(game)

        self.static_bg_surface: pg.Surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
        self.static_fg_surface: pg.Surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
        self.populate_static_surfaces()  # Must be called *after* creating the surfaces

        self.frame_durs: list[int | float] = []
        self.tick_durs: list[int | float] = []

    def populate_static_surfaces(self) -> None:
        # Draw elements to cached surface once to avoid
        # wasteful redraws.

        # Background rects
        draw_transparent_rect(  # Frame (left)
            self.static_bg_surface, (0, C.WN_H - self.DISPLAY_RECT_H),
            (self.DISPLAY_RECT_W, self.DISPLAY_RECT_H),
            border_thickness=self.DISPLAY_RECT_BORDER_W, bg_colour=(0, 0, 0, 140)
        )
        draw_transparent_rect(  # Tick (right)
            self.static_bg_surface, (C.WN_W - self.DISPLAY_RECT_W, C.WN_H - self.DISPLAY_RECT_H),
            (self.DISPLAY_RECT_W, self.DISPLAY_RECT_H),
            border_thickness=self.DISPLAY_RECT_BORDER_W, bg_colour=(0, 0, 0, 140)
        )

        # Foreground rects
        draw_transparent_rect(   # Frame (left)
            self.static_fg_surface, (0, C.WN_H - self.DISPLAY_RECT_H),
            (self.DISPLAY_RECT_W, self.DISPLAY_RECT_H),
            border_thickness=self.DISPLAY_RECT_BORDER_W, bg_colour=(0, 0, 0, 0)
        )
        draw_transparent_rect(  # Tick (right)
            self.static_fg_surface, (C.WN_W - self.DISPLAY_RECT_W, C.WN_H - self.DISPLAY_RECT_H),
            (self.DISPLAY_RECT_W, self.DISPLAY_RECT_H),
            border_thickness=self.DISPLAY_RECT_BORDER_W, bg_colour=(0, 0, 0, 0)
        )

        # Parameters for reference labels and lines
        label_size = 18
        label_colour = (255, 255, 255, 255)
        line_colour = (255, 255, 255, 255)
        label_font_family = self.game.assets.fonts.monospaced
        align_offset = 4

        # Middle line for FPS diagnostic
        pg.draw.line(
            self.static_fg_surface, line_colour,
            (0, C.WN_H - self.DISPLAY_RECT_H / 2),
            (self.DISPLAY_RECT_W, C.WN_H - self.DISPLAY_RECT_H / 2), width=1
        )

        # Text drawing - FPS
        draw_text(
            self.static_fg_surface, (align_offset, C.WN_H - self.DISPLAY_RECT_H), 'left', 'top',
            "30 FPS", label_colour, label_size, label_font_family
        )
        draw_text(
            self.static_fg_surface, (align_offset, C.WN_H - self.DISPLAY_RECT_H / 2), 'left', 'top',
            "60 FPS", label_colour, label_size, label_font_family
        )

        # Text drawing - TPS
        draw_text(
            self.static_fg_surface, (C.WN_W - self.DISPLAY_RECT_W + align_offset, C.WN_H - self.DISPLAY_RECT_H), 'left', 'top',
            "60 TPS", label_colour, label_size, label_font_family
        )

    def _plot_bars(self, surface: pg.Surface, plot_area: pg.Rect, values: list[float], max_ok: float, max_ok_h: float | None = None) -> None:
        """
        Draw a bar graph of values in bar_plot_rect.
        Bar colour ranges from (0, 255, 0) (green) for 0 to
        (255, 0, 0) (red) for max_ok, and red for any value greater than max_ok.

        A bar for the value of max_ok should be the height of max_ok_h, with linear
        scaling for other values. Height is not restricted or clamped.
        Bars extend upwards starting from the bottom of the plot area.
        """

        from pylines.core.colours import lerp_colours

        if max_ok_h is None:
            # If a max_ok_h is not given, assume that the maximum OK height
            # bar should extend to the very top of the plot area.
            
            max_ok_h = plot_area.bottom - plot_area.top

    def prune(self, max_len: int = MAX_HISTORY_LEN) -> None:
        if max_len <= 0:
            raise ValueError("prune: max_len must be a positive integer")

        self.frame_durs = self.frame_durs[-max_len:]
        self.tick_durs = self.tick_durs[-max_len:]

    def record_frame(self, dt_ms: int | float) -> None:
        self.frame_durs.append(dt_ms)

    def record_tick(self, dt_ms: int | float) -> None:
        self.tick_durs.append(dt_ms)

    def draw(self, surface: pg.Surface) -> None:

        # Blit cached background surface
        surface.blit(self.static_bg_surface, (0, 0))

        MAX_OK_DUR_FRAME = 1000 / C.FPS
        MAX_OK_DUR_TICK = 1000 / C.TPS

        # Draw FPS bars
        ...

        # Draw TPS bars
        ...

        # Blit cached foreground surface
        surface.blit(self.static_fg_surface, (0, 0))
