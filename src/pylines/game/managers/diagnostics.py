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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from statistics import mean
import time

import pygame as pg

import pylines.core.constants as C
from pylines.core.utils import draw_text, draw_transparent_rect, display_sf
from pylines.game.managers.pop_up_menus import PopupMenu
from pylines.debug.debug_display import DebugLog

if TYPE_CHECKING:
    from pylines.game.game import Game

@dataclass
class TimeInterval:
    """Records an initial and final time in seconds."""

    ti: float
    tf: float

    def duration(self) -> float:
        return self.tf - self.ti

    def duration_ms(self) -> float:
        return (self.tf - self.ti) * 1000

@dataclass
class Timespans:
    intervals: list[TimeInterval] = field(default_factory=list)

    def add_interval(self, obj) -> None:
        self.intervals.append(obj)

    def prune(self, max_len: int) -> None:
        if max_len <= 0:
            raise ValueError("max_len must be a positive integer (>0)")

        self.intervals = self.intervals[-max_len:]

    def get_intervals_from_last(self, t: float) -> list[TimeInterval]:
        """Get all the time intervals whose initial time is within the last t seconds"""

        now = time.perf_counter()
        cutoff = now - t
        return [interval for interval in self.intervals if interval.ti >= cutoff]

    def prune_seconds(self, t: float) -> None:
        """Prune intervals to only those whose initial time is within the last t seconds
        NOTE: this creates a new list with each call of this function"""

        self.intervals = self.get_intervals_from_last(t)

    def get_ms_durations(self) -> list[float]:
        return [t.duration_ms() for t in self.intervals]

class DiagnosticsManager(PopupMenu):
    DISPLAY_RECT_W: int = 600
    DISPLAY_RECT_H: int = 250
    DISPLAY_RECT_BORDER_W: int = 3

    _BAR_WIDTH: int = 3
    _MAX_INTERNAL_HISTORY_LEN_SECONDS: int = 10  # for getting last 10s counts
    MAX_HISTORY_LEN: int = (DISPLAY_RECT_W - 2 * DISPLAY_RECT_BORDER_W) // _BAR_WIDTH

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

        self.frame_durs: Timespans = Timespans()
        self.tick_durs: Timespans = Timespans()

        self.debug_log = DebugLog(game.assets.fonts.monospaced)

    def update_debug_log(self) -> None:
        # Prevent ZeroDivisionError from calculating FPS/TPS
        if (not self.frame_durs) or (not self.tick_durs):
            return

        self.debug_log.clear()
        self.debug_log.write(f"capable fps: {display_sf(1000 / mean(self.frame_durs.get_ms_durations()), 3)} (target: {C.FPS:.0f})")
        self.debug_log.write(f"capable tps: {1000 / mean(self.tick_durs.get_ms_durations()):,.0f} (target: {C.TPS:.0f})")

        self.debug_log.write(f"recent fps: {len(self.frame_durs.get_intervals_from_last(1))} (last 1s) | {len(self.frame_durs.get_intervals_from_last(10)) / 10:.1f} (last 10s)")
        self.debug_log.write(f"recent tps: {len(self.tick_durs.get_intervals_from_last(1))} (last 1s) | {len(self.tick_durs.get_intervals_from_last(10)) / 10:.1f} (last 10s)")

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
        label_size = 25
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
        Yellow (255, 255, 0) is used for values halfway between 0 and max_ok, with linear
        interpolation between green and yellow or yellow and red as required.

        A bar for the value of max_ok should be the height of max_ok_h, with linear
        scaling for other values. Height is not restricted or clamped.
        Bars extend upwards starting from the bottom of the plot area.
        """

        from pylines.core.colours import lerp_colours

        if max_ok_h is None:
            # If a max_ok_h is not given, assume that the maximum OK height
            # bar should extend to the very top of the plot area.

            max_ok_h = plot_area.bottom - plot_area.top

        if not values:
            raise ValueError("_plot_bars: requires values to plot")

        bar_count = min(len(values), max(1, plot_area.width))
        values = values[-bar_count:]

        bar_w = max(1, plot_area.width / bar_count)
        total_w = bar_w * bar_count
        left = plot_area.right - total_w

        baseline_y = plot_area.bottom
        green = (0, 255, 0)
        yellow = (255, 255, 0)
        red = (255, 0, 0)

        for i, value in enumerate(values):
            if max_ok <= 0:
                t = 0.0
                bar_h = 0.0
            else:
                t = max(0.0, min(1.0, value / max_ok))
                bar_h = (value / max_ok) * max_ok_h

            if bar_h <= 0:
                continue

            if t <= 0.5:
                colour = lerp_colours(green, yellow, t * 2)
            elif t < 1:
                colour = lerp_colours(yellow, red, (t - 0.5) * 2)
            else:
                # Use red for any value > max_ok
                colour = red

            x = left + i * bar_w
            y = baseline_y - bar_h

            pg.draw.rect(surface, colour, pg.Rect(x, y, bar_w, bar_h))

    def prune(self, t: int = _MAX_INTERNAL_HISTORY_LEN_SECONDS) -> None:
        if t <= 0:
            raise ValueError("prune: max_len must be a positive integer")

        self.frame_durs.prune_seconds(t)
        self.tick_durs.prune_seconds(t)

    def record_frame(self, interval: TimeInterval) -> None:
        self.frame_durs.add_interval(interval)

    def record_tick(self, interval: TimeInterval) -> None:
        self.tick_durs.add_interval(interval)

    def draw(self, surface: pg.Surface) -> None:
        # NOTE: animation_open is unused for draw() here as this is a diagnostic
        # that should instantly appear/disappear

        if not self.state.visible:
            return

        # Blit cached background surface
        surface.blit(self.static_bg_surface, (0, 0))
        self.prune()

        MAX_OK_DUR_FRAME = 1000 / C.FPS * 2  # 30 FPS = top of graph
        MAX_OK_DUR_TICK = 1000 / C.TPS       # 1 / C.TPS = top of graph
        # yeah I know they're different

        # Duration lists - convert to milliseconds
        frame_durs_floats: list[float] = self.frame_durs.get_ms_durations()
        tick_durs_floats: list[float] = self.tick_durs.get_ms_durations()

        # Draw FPS bars
        self._plot_bars(surface, self.frame_graph_plot_rect, frame_durs_floats, MAX_OK_DUR_FRAME)

        # Draw TPS bars
        self._plot_bars(surface, self.tick_graph_plot_rect, tick_durs_floats, MAX_OK_DUR_TICK)

        # Blit cached foreground surface
        surface.blit(self.static_fg_surface, (0, 0))

        # Compute min, avg, max
        text_colour = (255, 255, 255, 255)
        font_size = 25

        min_frame_dur = min(frame_durs_floats)
        avg_frame_dur = mean(frame_durs_floats)
        max_frame_dur = max(frame_durs_floats)

        min_tick_dur = min(tick_durs_floats)
        avg_tick_dur = mean(tick_durs_floats)
        max_tick_dur = max(tick_durs_floats)

        offset = 4
        num_sig_figs = 3

        # FPS min, avg, max
        draw_text(
            surface, (self.frame_graph_plot_rect.left + offset, self.frame_graph_plot_rect.top - offset), 'left', 'bottom',
            f"min: {display_sf(min_frame_dur, num_sig_figs)} ms", text_colour, font_size, self.game.assets.fonts.monospaced
        )
        draw_text(
            surface, (self.frame_graph_plot_rect.centerx, self.frame_graph_plot_rect.top - offset), 'centre', 'bottom',
            f"avg: {display_sf(avg_frame_dur, num_sig_figs)} ms", text_colour, font_size, self.game.assets.fonts.monospaced
        )
        draw_text(
            surface, (self.frame_graph_plot_rect.right - offset, self.frame_graph_plot_rect.top - offset), 'right', 'bottom',
            f"max: {display_sf(max_frame_dur, num_sig_figs)} ms", text_colour, font_size, self.game.assets.fonts.monospaced
        )

        # TPS min, avg, max
        draw_text(
            surface, (self.tick_graph_plot_rect.left + offset, self.tick_graph_plot_rect.top - offset), 'left', 'bottom',
            f"min: {display_sf(min_tick_dur, num_sig_figs)} ms", text_colour, font_size, self.game.assets.fonts.monospaced
        )
        draw_text(
            surface, (self.tick_graph_plot_rect.centerx, self.tick_graph_plot_rect.top - offset), 'centre', 'bottom',
            f"avg: {display_sf(avg_tick_dur, num_sig_figs)} ms", text_colour, font_size, self.game.assets.fonts.monospaced
        )
        draw_text(
            surface, (self.tick_graph_plot_rect.right - offset, self.tick_graph_plot_rect.top - offset), 'right', 'bottom',
            f"max: {display_sf(max_tick_dur, num_sig_figs)} ms", text_colour, font_size, self.game.assets.fonts.monospaced
        )

        # Debug summary
        self.debug_log.draw(surface)
