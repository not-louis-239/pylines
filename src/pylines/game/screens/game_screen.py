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

"""State management module for separating game state from other states"""

from __future__ import annotations

import ctypes
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Callable, Generator, Literal, cast

import numpy as np
import pygame as pg
from OpenGL import GL as gl

import pylines.core.colours as cols
import pylines.core.constants as C
from pylines.core.paths import DIRECTORIES
import pylines.core.units as units
from pylines.core.asset_manager import FLine
from pylines.core.asset_manager_helpers import ControlsSectionID
from pylines.core.custom_types import AColour, Colour, EventList, RealNumber
from pylines.core.time_manager import (
    fetch_hour,
    sky_colour_from_hour,
    sun_direction_from_hour,
    sunlight_strength_from_hour,
)
from pylines.core.utils import (
    clamp,
    draw_needle,
    draw_text,
    draw_transparent_rect,
    frange,
    wrap_text,
    get_lerp_weight
)
from pylines.game.states import State, StateID
from pylines.objects.buildings import (
    BuildingDefinition,
    BuildingMapIconType,
    draw_building_icon,
)
from pylines.objects.buttons import Button, ImageButton
from pylines.objects.objects import CrashReason, Plane
from pylines.objects.scenery.ground import Ground
from pylines.objects.scenery.ocean import Ocean
from pylines.game.managers.cockpit_renderer import CockpitRenderer
from pylines.objects.scenery.sky import Moon, Sky, Sun
from pylines.shaders.shader_manager import load_shader_script
from pylines.game.managers.smoke_manager import SmokeManager
from pylines.objects.rotation_input_container import RotationInputContainer
from pylines.core.asset_manager_helpers import ControlsSectionID, ControlsSection, MusicID
from pylines.game.managers.jukebox import Jukebox

if TYPE_CHECKING:
    from pylines.core.custom_types import ScancodeWrapper, Surface
    from pylines.game.game import Game

class Visibility(Enum):
    HIDDEN = 0
    SHOWN = 1

    @staticmethod
    def toggle(current: Visibility) -> Visibility:
        return Visibility.HIDDEN if current == Visibility.SHOWN else Visibility.SHOWN

@dataclass
class DialogMessage:
    active_time: int = 0  # milliseconds
    colour: Colour = cols.WHITE
    msg: str = ''

    def set_message(self, msg: str, colour: Colour = cols.WHITE, active_time: int = 2500):
        self.active_time = active_time
        self.msg = msg
        self.colour = colour

    def reset(self):
        self.set_message('', cols.WHITE, 0)

    def update(self, dt: int):
        self.active_time = max(self.active_time - dt, 0)

class GameScreen(State):
    def __init__(self, game: Game) -> None:
        """Purposefully lightweight constructor
        to avoid stalling during loading screen."""

        assets = game.assets
        super().__init__(game)
        assert self.game.env is not None

        self.warn_stall: bool = False
        self.warn_overspeed: bool = False
        self.time_elapsed: int = 0  # milliseconds

        self.dialog_box = DialogMessage()

        self.sky = Sky()
        self.sun = Sun(assets.images.sun)
        self.moon = Moon(assets.images.moon)
        self.plane = Plane(assets.sounds, self.dialog_box, self.game.env, RotationInputContainer())

        self.auto_screenshots_enabled: bool = False
        self.auto_screenshot_interval_ms: int = 30_000
        self._auto_screenshot_elapsed_ms: int = 0
        self._auto_screenshot_pending: bool = False

        self.channel_music = self.game.music_channel
        self.channel_engine_ambient = pg.mixer.Channel(C.SFXChannelID.ENGINE_AMBIENT)
        self.channel_engine_active = pg.mixer.Channel(C.SFXChannelID.ENGINE_ACTIVE)
        self.channel_wind = pg.mixer.Channel(C.SFXChannelID.WIND)

        self.channel_stall = pg.mixer.Channel(C.SFXChannelID.STALL)
        self.channel_overspeed = pg.mixer.Channel(C.SFXChannelID.OVERSPEED)
        self.channel_prohibited = pg.mixer.Channel(C.SFXChannelID.PROHIBITED)

        self.channel_scrape = pg.mixer.Channel(C.SFXChannelID.SCRAPE)

        # GPS destination
        self.gps_runway_index: int = 1  # start at second GPS destination

        # Pausing
        self.paused: bool = False

        # Font for text rendering
        self.font = pg.font.Font(assets.fonts.monospaced, 36)

        # Confirmation menus
        self.in_menu_confirmation: bool = False
        self.in_restart_confirmation: bool = False
        self.in_controls_screen: bool = False

        self.in_help_screen: bool = False
        self.help_screen_offset: float = 0
        self.help_max_offset: float = 0
        self.help_scroll_vel: float = 0

        # Menu states
        self.jukebox_menu_surface: Surface = pg.Surface((540, 600), flags=pg.SRCALPHA)
        self.jukebox_menu_up: RealNumber = 0
        self.jukebox_menu_state: Visibility = Visibility.HIDDEN

        self.controls_quick_ref_up: RealNumber = 0  # represents how active it is
        self.controls_quick_ref_state: Visibility = Visibility.HIDDEN

        self.continue_button = Button(
            (C.WN_W//2-400, C.WN_H//2), 250, 50, (0, 96, 96), (128, 255, 255),
            "Continue", self.fonts.monospaced, 30
        )
        self.restart_button = Button(
            (C.WN_W//2, C.WN_H//2), 250, 50, (0, 96, 96), (128, 255, 255),
            "Restart", self.fonts.monospaced, 30
        )
        self.menu_button = Button(
            (C.WN_W//2+400, C.WN_H//2), 250, 50, (0, 96, 96), (128, 255, 255),
            "Return to Menu", self.fonts.monospaced, 30
        )

        self.yes_button = Button(
            (C.WN_W//2-200, C.WN_H//2+20), 150, 50, (0, 96, 96), (128, 255, 255),
            "Yes", self.fonts.monospaced, 30
        )
        self.no_button = Button(
            (C.WN_W//2+200, C.WN_H//2+20), 150, 50, (0, 96, 96), (128, 255, 255),
            "No", self.fonts.monospaced, 30
        )

        self.controls_button = Button(
            (C.WN_W//2, C.WN_H - 100), 250, 50, (0, 96, 96), (128, 255, 255),
            "Controls", self.fonts.monospaced, 30
        )
        self.back_button = Button(
            (C.WN_W//2, C.WN_H - 70), 250, 50, (0, 96, 96), (128, 255, 255),
            "Back", self.fonts.monospaced, 30
        )
        self.crash_screen_restart_button = Button(
            (C.WN_W//2, C.WN_H//2 + 30), 180, 50, (0, 96, 96), (128, 255, 255),
            "Restart", self.fonts.monospaced, 30
        )

        self.help_button = ImageButton((C.WN_W - 75, C.WN_H - 75), self.images.help_icon)

        # Graphics
        self.hud_tex = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.hud_tex)

        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

        # Allocate empty texture
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, C.WN_W, C.WN_H, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None)

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        self.hud_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)

        self.map_surface = pg.Surface((C.MAP_OVERLAY_SIZE, C.MAP_OVERLAY_SIZE), pg.SRCALPHA)
        self.map_surface.fill((0, 0, 0, 255))

        self.grid_surface = pg.Surface((C.MAP_OVERLAY_SIZE, C.MAP_OVERLAY_SIZE), pg.SRCALPHA)
        self.grid_surface.fill((0, 0, 0, 0))

        self.zone_overlay = pg.Surface((C.MAP_OVERLAY_SIZE, C.MAP_OVERLAY_SIZE), pg.SRCALPHA)
        self.zone_overlay.fill((0, 0, 0, 0))

        # Cache rotated compasses to save resources when drawing
        self.cockpit_renderer = CockpitRenderer(self.game, self.plane)
        self.show_cockpit: bool = True  # Start with cockpit visible

        self.grid_labels_x: dict[int, pg.Surface] = {}
        self.grid_labels_y: dict[int, pg.Surface] = {}
        self.grid_detail_level: int | None = None

        # Build quick ref for controls
        self.controls_quick_ref_surface = self._populate_controls_quick_ref()

        # Star rendering cache (VBO)
        self._star_dirs: np.ndarray | None = None
        self._star_colors: np.ndarray | None = None
        self._star_brightness: np.ndarray | None = None
        self._star_base_positions: np.ndarray | None = None
        self._star_vbo: int | None = None
        self._star_color_vbo: int | None = None
        self._star_count: int = 0
        self._star_cache_key: tuple[float, float] | None = None

        self.smoke_manager = SmokeManager(assets.images)
        self.jukebox = Jukebox(self.game.assets.sounds.jukebox_tracks)

    def reset(self) -> None:
        self.in_menu_confirmation = False
        self.in_restart_confirmation = False
        self.paused = False

        self.plane.reset()
        self.gps_runway_index = 1

        self.channel_wind.stop()
        self.channel_engine_active.stop()
        self.channel_engine_ambient.stop()

        self.channel_stall.stop()
        self.channel_overspeed.stop()

        self.channel_scrape.stop()

        self.sounds.jukebox_tracks[MusicID.OPEN_TWILIGHT].fadeout(1_500)
        self.dialog_box.reset()
        self.time_elapsed = 0

    def _populate_ai_surface(self) -> Surface:
        width = 170 - 4
        height = 2000
        surf = pg.Surface((width, height), pg.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        tick_spacing = 5  # pixels per 5° of pitch
        centre_y = height // 2

        for deg in range(-180, 185, 5):  # pitch marks in degrees
            if deg == 0:
                line_width = 85
            elif deg % 10 == 0:
                line_width = 30
            else:
                line_width = 15

            y = centre_y + deg * tick_spacing
            if 0 <= y <= height:
                pg.draw.line(
                    surf,
                    cols.WHITE,
                    (width//2 - line_width, y),
                    (width//2 + line_width, y),
                    3
                )

                if deg % 10 == 0 and deg != 0:
                    if -90 <= deg <= 90:
                        deg_display_value = deg
                    elif deg < -90:
                        deg_display_value = -180 - deg
                    else:
                        deg_display_value = 180 - deg

                    draw_text(
                        surf, (width//2 + line_width + 5, y), 'left', 'centre',
                        str(abs(deg_display_value)), cols.WHITE, 19, self.fonts.monospaced
                    )
                    draw_text(
                        surf, (width//2 - line_width - 5, y), 'right', 'centre',
                        str(abs(deg_display_value)), cols.WHITE, 19, self.fonts.monospaced
                    )

        return surf

    def _populate_building_legend(self) -> Surface:
        assert self.game.env is not None

        width, height = 200, 360
        surf = pg.Surface((width, height), pg.SRCALPHA)
        surf.fill((0, 0, 0, 180))
        pg.draw.rect(surf, cols.MAP_BORDER_COLOUR, surf.get_rect(), 2)

        draw_text(surf, (100, 25), 'centre', 'centre', "Buildings", cols.WHITE, 20, self.fonts.monospaced)

        items = list(self.game.env.building_defs.items())

        def icon_height(info: BuildingDefinition) -> int:
            icon = info.appearance.icon
            dims = info.appearance.dims
            if icon == BuildingMapIconType.POINT:
                return 0
            if icon == BuildingMapIconType.CIRCLE:
                return cast(tuple[int], dims)[0] * 2
            if icon == BuildingMapIconType.SQUARE:
                return cast(tuple[int, int], dims)[1]
            return 0

        screen_y = 60
        for idx, (name, def_) in enumerate(items):
            draw_text(surf, (75, screen_y), 'left', 'centre', f"{def_.common_name}", cols.WHITE, 15, self.fonts.monospaced)
            draw_building_icon(surf, 35, screen_y, def_.appearance)

            curr_h = icon_height(def_)
            next_h = icon_height(items[idx + 1][1]) if idx + 1 < len(items) else 0
            line_h = max(15, 15 + curr_h//2 + next_h//2)
            screen_y += line_h

        return surf

    def _populate_height_legend(self) -> Surface:
        width, height = 180, 360
        surf = pg.Surface((width, height), pg.SRCALPHA)
        surf.fill((0, 0, 0, 180))
        pg.draw.rect(surf, cols.MAP_BORDER_COLOUR, surf.get_rect(), 2)

        draw_text(surf, (90, 25), 'centre', 'centre', "Altitude (ft)", cols.WHITE, 20, self.fonts.monospaced)
        surf.blit(self.height_key, (105, 55))

        for h in range(-12_000, 18_001, 2_000):
            text_y = 55 + (self.HEIGHT_KEY_H * (1 - ((h + 12_000) / 30_000)))
            draw_text(surf, (100, text_y), 'right', 'centre', f"{h:,.0f}", cols.WHITE, 15, self.fonts.monospaced)

        return surf

    def _populate_controls_quick_ref(self) -> Surface:
        """Draw everything to a cached surface for the controls mini-reference
        to avoid wasting resources drawing it each frame while active."""

        surf = pg.Surface((400, 600), flags=pg.SRCALPHA)

        surf.fill((0, 0, 0, 180))
        pg.draw.rect(surf, cols.WHITE, surf.get_rect(), 2)  # 2px-wide white border

        title_y = 30
        draw_text(surf, (35, title_y), 'left', 'centre', "Controls (Quick Ref)", cols.WHITE, 24, self.fonts.monospaced)

        def draw_section(title: str, start_y: int, items: dict[str, str]) -> int:
            draw_text(surf, (35, start_y), 'left', 'centre', title, (0, 192, 255), 20, self.fonts.monospaced)
            y = start_y + 35
            for key, desc in items.items():
                draw_text(surf, (35, y), 'left', 'centre', key, (150, 230, 255), 16, self.fonts.monospaced)
                draw_text(surf, (110, y), 'left', 'centre', desc, cols.WHITE, 16, self.fonts.monospaced)
                y += 20
            return y

        y = 75
        y = draw_section(
            "Main Controls",
            y,
            self.game.assets.texts.controls_sections[ControlsSectionID.MAIN].keys
        )

        y += 10
        y = draw_section(
            "Displays",
            y,
            self.game.assets.texts.controls_sections[ControlsSectionID.DISPLAYS].keys,
        )

        y += 10
        y = draw_section(
            "While Map Open",
            y,
            self.game.assets.texts.controls_sections[ControlsSectionID.MAP].keys,
        )

        y += 10
        y = draw_section(
            "Utilities",
            y,
            self.game.assets.texts.controls_sections[ControlsSectionID.UTILITIES].keys,
        )

        draw_text(surf, (200, 575), 'centre', 'centre', "Press O to close", (150, 230, 255), 18, self.fonts.monospaced)

        return surf

    def _build(self) -> Generator[tuple[float, str], None, None]:
        yield from self._init_ground(0.3, 0.45)

        self._init_ocean()
        yield 0.7, "Adding H₂O"

        self._init_buildings()
        yield 0.85, "Making cities"

        self._init_map()
        yield 0.95, "Booting up GPS"

    def _init_ground(self, start: float, end: float):
        assert self.game.env is not None

        assets = self.game.assets
        ground_textures = {
            "sand_texture": assets.images.sand,
            "low_grass_texture": assets.images.low_grass,
            "high_grass_texture": assets.images.high_grass,
            "treeline_rock_texture": assets.images.treeline_rock,
            "alpine_rock_texture": assets.images.alpine_rock,
            "snow_texture": assets.images.snow,
            "noise": assets.world.noise,
        }

        self.ground = Ground(ground_textures, self.game.env)

        span = end - start
        for p, msg in self.ground._build():
            yield start + p * span, msg

    def _init_ocean(self):
        assert self.game.env is not None

        self.ocean = Ocean(self.game.assets.images.ocean, self.game.env)

    def _init_buildings(self):
        assert self.game.env is not None

        # Building rendering setup
        all_vertices = []
        for building in self.game.env.buildings:
            all_vertices.extend(building.get_vertices())

        if all_vertices:
            self.building_vertices = np.array(all_vertices, dtype=np.float32)
            self.building_vertex_count = len(self.building_vertices) // 10

            self.buildings_vbo = gl.glGenBuffers(1)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buildings_vbo)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, self.building_vertices.nbytes, self.building_vertices, gl.GL_STATIC_DRAW)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

            self.building_shader = load_shader_script(
                DIRECTORIES.src.shaders / "building.vert",
                DIRECTORIES.src.shaders / "building.frag"
            )
            self.building_pos_loc = gl.glGetAttribLocation(self.building_shader, "position")
            self.building_color_loc = gl.glGetAttribLocation(self.building_shader, "color")
            self.building_normal_loc = gl.glGetAttribLocation(self.building_shader, "normal")
            self.building_emissive_loc = gl.glGetAttribLocation(self.building_shader, "in_emissive")
            self.building_brightness_loc = gl.glGetUniformLocation(self.building_shader, "u_brightness")
            self.building_sun_direction_loc = gl.glGetUniformLocation(self.building_shader, "u_sun_direction")
            self.building_min_brightness_loc = gl.glGetUniformLocation(self.building_shader, "u_min_brightness")
            self.building_max_brightness_loc = gl.glGetUniformLocation(self.building_shader, "u_max_brightness")
            self.building_shade_multiplier_loc = gl.glGetUniformLocation(self.building_shader, "u_shade_multiplier")
        else:
            self.building_vertices = np.array([], dtype=np.float32)
            self.building_vertex_count = 0
            self.buildings_vbo = None

    def _init_map(self):
        assert self.game.env is not None

        # Map view setup
        self.map_up: RealNumber = 0  # 1 = fully up, 0 = fully down
        self.map_state: Visibility = Visibility.HIDDEN
        self.map_show_advanced_info = False

        def height_to_colour(h: float) -> Colour:
            lerp_colour: Callable = cols.lerp_colours

            THRESHOLDS: list[tuple[float, Colour]] = [
                (6000, (177, 192, 204)),
                (5500, (113, 122, 130)),
                (5000, (79, 79, 79)),
                (4000, (38, 38, 38)),
                (2200, (94, 61, 39)),
                (800,  (10, 99, 5)),
                (150,  (23, 143, 49)),
                (0,    (224, 207, 162)),
                (-0.01,(84, 156, 240)),
                (-200, (43, 118, 204)),
                (-500, (37, 59, 179)),
                (-1_000, (18, 36, 130)),
                (-4_000, (7, 18, 74))
            ]

            # Sort descending by threshold
            THRESHOLDS.sort(reverse=True, key=lambda t: t[0])

            # Below the lowest threshold
            if h <= THRESHOLDS[-1][0]:
                return THRESHOLDS[-1][1]

            # Find the interval to interpolate
            for i in range(len(THRESHOLDS) - 1):
                high_h, high_c = THRESHOLDS[i]
                low_h, low_c = THRESHOLDS[i+1]
                if low_h <= h <= high_h:
                    t = (h - low_h) / (high_h - low_h)
                    return lerp_colour(low_c, high_c, t)

            # Above the highest threshold
            return THRESHOLDS[0][1]

        self.map_height_to_colour = height_to_colour

        # Precompute height-colour relationship to avoid wasteful function calls
        HEIGHT_COLOUR_LOOKUP = [height_to_colour(h) for h in range(-4_000, 6_001)]

        NUM_TILES = math.ceil(C.HALF_WORLD_SIZE*2 / (C.METRES_PER_TILE))
        self.map_tiles: list[list[pg.Surface]] = []

        # Make cache directory if it doesn't exist
        cache_dir = DIRECTORIES.cache / "map_tiles"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Loop over tiles
        for tile_z in range(NUM_TILES):
            tile_row: list[pg.Surface] = []
            for tile_x in range(NUM_TILES):
                tile_filename = f"tile_{tile_x}_{tile_z}.png"
                tile_cache_path = cache_dir / tile_filename

                if tile_cache_path.exists():
                    current_tile = pg.image.load(str(tile_cache_path)).convert()
                    tile_row.append(current_tile)
                    continue

                tile_start_x = -C.HALF_WORLD_SIZE + C.METRES_PER_TILE * tile_x
                tile_start_z = -C.HALF_WORLD_SIZE + C.METRES_PER_TILE * tile_z

                # Make a new Surface for each tile
                current_tile = pg.Surface((C.MAP_PIXELS_PER_TILE, C.MAP_PIXELS_PER_TILE)).convert()

                # Vectorized tile sampling from heightmap
                env = self.game.env
                height_arr = env.height_array
                hmap_h, hmap_w = height_arr.shape

                xs = tile_start_x + np.arange(C.MAP_PIXELS_PER_TILE, dtype=np.float32) * C.MAP_METRES_PER_PX
                zs = tile_start_z + np.arange(C.MAP_PIXELS_PER_TILE, dtype=np.float32) * C.MAP_METRES_PER_PX

                ix = (xs + C.HALF_WORLD_SIZE) / (2 * C.HALF_WORLD_SIZE) * hmap_w
                iz = (zs + C.HALF_WORLD_SIZE) / (2 * C.HALF_WORLD_SIZE) * hmap_h

                ix_grid, iz_grid = np.meshgrid(ix, iz, indexing='xy')
                ix_grid = np.clip(ix_grid, 0, hmap_w - (1 + C.MATH_EPSILON))
                iz_grid = np.clip(iz_grid, 0, hmap_h - (1 + C.MATH_EPSILON))

                x1 = ix_grid.astype(np.int32)
                y1 = iz_grid.astype(np.int32)
                x2 = np.clip(x1 + 1, 0, hmap_w - 1)
                y2 = np.clip(y1 + 1, 0, hmap_h - 1)

                fx = ix_grid - x1
                fy = iz_grid - y1

                h00 = height_arr[y1, x1]
                h10 = height_arr[y1, x2]
                h01 = height_arr[y2, x1]
                h11 = height_arr[y2, x2]

                if env.diagonal_split == 'AD':
                    mask = fy < fx
                    u = np.where(mask, 1 - fx, 1 - fy)
                    v = np.where(mask, fx - fy, fy - fx)
                    w = np.where(mask, fy, fx)
                    interp = np.where(
                        mask,
                        u * h00 + v * h10 + w * h11,
                        u * h00 + v * h01 + w * h11
                    )
                else:
                    mask = (1 - fx) > fy
                    u = np.where(mask, 1 - fx - fy, 1 - fy)
                    v = np.where(mask, fx, 1 - fx)
                    w = np.where(mask, fy, fx + fy - 1)
                    interp = u * h00 + v * h10 + w * h01

                raw_height = env.min_h + (interp / 65535.0) * (env.max_h - env.min_h)
                idx = np.clip(raw_height, -4_000, 6_000).astype(np.int32) + 4_000

                lookup = np.asarray(HEIGHT_COLOUR_LOOKUP, dtype=np.uint8)
                colours = lookup[idx]

                pixels = pg.surfarray.pixels3d(current_tile)
                pixels[:] = colours.swapaxes(0, 1)
                del pixels
                pg.image.save(current_tile, str(tile_cache_path))

                tile_row.append(current_tile)
            self.map_tiles.append(tile_row)

        self.viewport_zoom = 50  # metres per pixel of map shown
        self.viewport_pos = pg.Vector3(self.plane.pos)
        self.viewport_auto_panning = True

        # Height key setup
        self.HEIGHT_KEY_W = 25
        self.HEIGHT_KEY_H = 280
        self.height_key: pg.Surface = pg.Surface((self.HEIGHT_KEY_W, self.HEIGHT_KEY_H))

        for i in range(self.HEIGHT_KEY_H):
            # i goes from 0 (top) to self.HEIGHT_KEY_H - 1 (bottom)
            # We want h to go from 6_000 (top) to -4_000 (bottom)
            h = 6_000 - (10_000 * i / (self.HEIGHT_KEY_H - 1))
            pg.draw.rect(self.height_key, HEIGHT_COLOUR_LOOKUP[int(h+4000)], pg.Rect(0, i, self.HEIGHT_KEY_W, 1))

        self.building_legend_surface = self._populate_building_legend()
        self.height_legend_surface = self._populate_height_legend()

    def take_screenshot(self, *, notify: bool = True) -> None:
        DIRECTORIES.data.screenshots.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = DIRECTORIES.data.screenshots / filename

        width, height = C.WN_W, C.WN_H
        gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)

        # Read RGB only to avoid alpha artifacts from the framebuffer
        pixel_data = gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)

        assert isinstance(pixel_data, bytes)  # avoids static type checker errors
        surface = pg.image.frombuffer(pixel_data, (width, height), "RGB")
        surface = pg.transform.flip(surface, False, True)
        pg.image.save(surface, str(filepath))

        if notify:
            self.dialog_box.set_message(f"Screenshot saved: {filename}", (255, 240, 209))  # light yellow colour

    def draw_buildings(self, cloud_attenuation: float):
        if not self.building_vertex_count or self.buildings_vbo is None:
            return

        gl.glUseProgram(self.building_shader)

        # Set uniforms
        current_hour = fetch_hour()
        brightness = sunlight_strength_from_hour(current_hour) * cloud_attenuation
        sun_direction = sun_direction_from_hour(current_hour)

        gl.glUniform1f(self.building_brightness_loc, brightness)
        gl.glUniform3f(self.building_sun_direction_loc, sun_direction.x, sun_direction.y, sun_direction.z)
        gl.glUniform1f(self.building_min_brightness_loc, C.MOON_BRIGHTNESS)
        gl.glUniform1f(self.building_max_brightness_loc, C.SUN_BRIGHTNESS)
        gl.glUniform1f(self.building_shade_multiplier_loc, C.SHADE_BRIGHTNESS_MULT)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buildings_vbo)

        stride = 10 * ctypes.sizeof(ctypes.c_float)

        # Position
        gl.glEnableVertexAttribArray(self.building_pos_loc)
        gl.glVertexAttribPointer(self.building_pos_loc, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(0))

        # Color
        gl.glEnableVertexAttribArray(self.building_color_loc)
        gl.glVertexAttribPointer(self.building_color_loc, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))

        # Normal
        gl.glEnableVertexAttribArray(self.building_normal_loc)
        gl.glVertexAttribPointer(self.building_normal_loc, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(6 * ctypes.sizeof(ctypes.c_float)))

        # Emissive
        gl.glEnableVertexAttribArray(self.building_emissive_loc)
        gl.glVertexAttribPointer(self.building_emissive_loc, 1, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(9 * ctypes.sizeof(ctypes.c_float)))

        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self.building_vertex_count)

        gl.glDisableVertexAttribArray(self.building_pos_loc)
        gl.glDisableVertexAttribArray(self.building_color_loc)
        gl.glDisableVertexAttribArray(self.building_normal_loc)
        gl.glDisableVertexAttribArray(self.building_emissive_loc)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glUseProgram(0)

    def draw_stars(self) -> None:
        assert self.game.env is not None

        hour = fetch_hour()
        if 18 >= hour > 6:  # daytime
            opacity = 0
        elif 20 >= hour > 18:  # sunset
            opacity = (hour - 18) / 2
        elif 6 >= hour > 4:  # sunrise
            opacity = 1 - (hour - 4) / 2
        else:  # night
            opacity = 1

        opacity = clamp(opacity, (0, 1))
        if opacity == 0:
            return

        # Initialize star buffers if needed
        if self._star_dirs is None:
            dirs = np.array([s.direction for s in self.game.env.stars], dtype=np.float32)
            # Normalize directions once safely
            norms = np.linalg.norm(dirs, axis=1, keepdims=True)
            norms[norms == 0] = 1
            self._star_dirs = dirs / norms
            self._star_colors = np.array([s.colour for s in self.game.env.stars], dtype=np.float32) / 255.0
            self._star_brightness = np.array([s.brightness for s in self.game.env.stars], dtype=np.float32)
            self._star_count = len(self.game.env.stars)

            # Create VBOs
            self._star_vbo = gl.glGenBuffers(1)
            self._star_color_vbo = gl.glGenBuffers(1)

        # Cache base positions when hour bucket or opacity changes; apply camera offset each frame
        assert self._star_brightness is not None
        assert self._star_dirs is not None

        hour_bucket = round(fetch_hour(), 2)
        cache_key = (hour_bucket, round(opacity, 3))
        if self._star_cache_key != cache_key or self._star_base_positions is None:
            sun_dir = sun_direction_from_hour(hour_bucket)
            ref_dir = np.array([0.0, 0.0, -1.0], dtype=np.float32)
            sun = np.array([sun_dir.x, sun_dir.y, sun_dir.z], dtype=np.float32)

            k = np.cross(ref_dir, sun)
            k_norm = np.linalg.norm(k)
            if k_norm < C.MATH_EPSILON:
                if np.dot(ref_dir, sun) > 0:
                    rotated = self._star_dirs
                else:
                    rotated = -self._star_dirs
            else:
                k = k / k_norm
                cos_theta = np.clip(np.dot(ref_dir, sun), -1.0, 1.0)
                theta = math.acos(cos_theta)
                sin_t = math.sin(theta)
                v = self._star_dirs
                rotated = (
                    v * cos_theta +
                    np.cross(k, v) * sin_t +
                    k * (np.dot(v, k))[:, None] * (1 - cos_theta)
                )

            norms = np.linalg.norm(rotated, axis=1, keepdims=True)
            norms[norms == 0] = 1
            self._star_base_positions = (rotated / norms) * 1000

            colors = np.empty((self._star_count, 4), dtype=np.float32)
            colors[:, :3] = self._star_colors
            colors[:, 3] = self._star_brightness * opacity

            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self._star_color_vbo)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, colors.nbytes, colors, gl.GL_DYNAMIC_DRAW)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

            self._star_cache_key = cache_key

        assert self._star_base_positions is not None
        camera_pos = np.array(
            [self.plane.pos.x, self.plane.pos.y + C.CAMERA_RADIUS, self.plane.pos.z],
            dtype=np.float32,
        )
        positions = self._star_base_positions + camera_pos

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self._star_vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, positions.nbytes, positions, gl.GL_DYNAMIC_DRAW)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

        # Save OpenGL states
        was_blend_enabled = gl.glIsEnabled(gl.GL_BLEND)
        was_depth_mask_enabled = gl.glGetBooleanv(gl.GL_DEPTH_WRITEMASK)
        was_depth_test_enabled = gl.glIsEnabled(gl.GL_DEPTH_TEST)
        current_point_size = gl.glGetFloatv(gl.GL_POINT_SIZE)
        was_texture_2d_enabled = gl.glIsEnabled(gl.GL_TEXTURE_2D)

        # Configure GL for point rendering
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDepthMask(gl.GL_FALSE)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glPointSize(2.0)

        # Enable vertex/color arrays
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_COLOR_ARRAY)

        # Bind VBOs
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self._star_vbo)
        gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self._star_color_vbo)
        gl.glColorPointer(4, gl.GL_FLOAT, 0, None)

        # Draw stars
        gl.glDrawArrays(gl.GL_POINTS, 0, self._star_count)

        # Cleanup
        gl.glDisableClientState(gl.GL_COLOR_ARRAY)
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

        # Restore OpenGL states
        if was_depth_test_enabled:
            gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glPointSize(current_point_size)
        gl.glDepthMask(was_depth_mask_enabled)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        if was_texture_2d_enabled:
            gl.glEnable(gl.GL_TEXTURE_2D)
        if not was_blend_enabled:
            gl.glDisable(gl.GL_BLEND)

    def draw_map(self):
        assert self.game.env is not None

        pitch, yaw, roll = self.plane.get_rot()

        self.map_surface.fill((0, 0, 0, 255))
        NUM_TILES = math.ceil(C.HALF_WORLD_SIZE*2 / (C.METRES_PER_TILE))

        if self.viewport_auto_panning:
            self.viewport_pos = self.plane.pos.copy()

        px, _, pz = self.viewport_pos

        # Render base map
        map_centre = C.WN_W//2, int(285 + C.WN_H * (1-self.map_up))

        # Map border
        outer_map_rect = pg.Rect(0, 0, C.MAP_OVERLAY_SIZE+10, C.MAP_OVERLAY_SIZE+10)
        outer_map_rect.center = map_centre
        pg.draw.rect(self.hud_surface, cols.MAP_BORDER_COLOUR, outer_map_rect)

        # Draw map tiles
        # World coordinates of the top-left corner of the map viewport
        viewport_half_size_metres = C.MAP_OVERLAY_SIZE / 2 * self.viewport_zoom
        viewport_top_left_x = px - viewport_half_size_metres
        viewport_top_left_z = pz - viewport_half_size_metres

        # Tile indices for the visible area
        start_tile_x = int((viewport_top_left_x + C.HALF_WORLD_SIZE) / C.METRES_PER_TILE)
        start_tile_z = int((viewport_top_left_z + C.HALF_WORLD_SIZE) / C.METRES_PER_TILE)
        end_tile_x = int((viewport_top_left_x + 2 * viewport_half_size_metres + C.HALF_WORLD_SIZE) / C.METRES_PER_TILE)
        end_tile_z = int((viewport_top_left_z + 2 * viewport_half_size_metres + C.HALF_WORLD_SIZE) / C.METRES_PER_TILE)

        # Draw tiles
        for tile_z in range(start_tile_z, end_tile_z + 1):
            for tile_x in range(start_tile_x, end_tile_x + 1):
                if not (0 <= tile_x < NUM_TILES and 0 <= tile_z < NUM_TILES):
                    continue

                tile_surface = self.map_tiles[tile_z][tile_x]

                tile_world_x = -C.HALF_WORLD_SIZE + tile_x * C.METRES_PER_TILE
                tile_world_z = -C.HALF_WORLD_SIZE + tile_z * C.METRES_PER_TILE
                tile_world_x2 = tile_world_x + C.METRES_PER_TILE
                tile_world_z2 = tile_world_z + C.METRES_PER_TILE

                inter_left = max(tile_world_x, viewport_top_left_x)
                inter_top = max(tile_world_z, viewport_top_left_z)
                inter_right = min(tile_world_x2, viewport_top_left_x + 2 * viewport_half_size_metres)
                inter_bottom = min(tile_world_z2, viewport_top_left_z + 2 * viewport_half_size_metres)

                if inter_left >= inter_right or inter_top >= inter_bottom:
                    continue

                px_per_m = tile_surface.get_width() / C.METRES_PER_TILE
                src_x = (inter_left - tile_world_x) * px_per_m
                src_y = (inter_top - tile_world_z) * px_per_m
                src_w = (inter_right - inter_left) * px_per_m
                src_h = (inter_bottom - inter_top) * px_per_m

                dest_x = (inter_left - viewport_top_left_x) / self.viewport_zoom
                dest_y = (inter_top - viewport_top_left_z) / self.viewport_zoom
                dest_w = (inter_right - inter_left) / self.viewport_zoom
                dest_h = (inter_bottom - inter_top) / self.viewport_zoom

                src_left = int(math.floor(src_x))
                src_top = int(math.floor(src_y))
                src_right = int(math.ceil(src_x + src_w))
                src_bottom = int(math.ceil(src_y + src_h))

                src_left = max(0, min(src_left, tile_surface.get_width()))
                src_top = max(0, min(src_top, tile_surface.get_height()))
                src_right = max(0, min(src_right, tile_surface.get_width()))
                src_bottom = max(0, min(src_bottom, tile_surface.get_height()))

                if src_right <= src_left or src_bottom <= src_top:
                    continue

                src_rect = pg.Rect(src_left, src_top, src_right - src_left, src_bottom - src_top)

                world_left = tile_world_x + (src_left / px_per_m)
                world_top = tile_world_z + (src_top / px_per_m)
                world_w = (src_rect.w / px_per_m)
                world_h = (src_rect.h / px_per_m)

                dest_x = (world_left - viewport_top_left_x) / self.viewport_zoom
                dest_y = (world_top - viewport_top_left_z) / self.viewport_zoom
                dest_w = world_w / self.viewport_zoom
                dest_h = world_h / self.viewport_zoom
                dest_rect = pg.Rect(dest_x, dest_y, dest_w, dest_h)

                tile_crop = tile_surface.subsurface(src_rect)
                scaled_tile = pg.transform.scale(tile_crop, (max(1, int(dest_rect.w) + 1), max(1, int(dest_rect.h) + 1)))
                self.map_surface.blit(scaled_tile, dest_rect)


        # Show buildings
        if self.viewport_zoom < 10:  # Only show if zoomed in far enough for performance
            for building in self.game.env.buildings:
                # Calculate screen position for the building
                screen_x = (building.pos.x - viewport_top_left_x) / self.viewport_zoom
                screen_y = (building.pos.z - viewport_top_left_z) / self.viewport_zoom

                SAFETY_BUFFER = 25  # for smoothness
                if (-SAFETY_BUFFER < screen_x < C.MAP_OVERLAY_SIZE + SAFETY_BUFFER
                and -SAFETY_BUFFER < screen_y < C.MAP_OVERLAY_SIZE + SAFETY_BUFFER):
                    # Retrieve building definition
                    def_ = self.game.env.building_defs[building.type_]

                    # Draw the building icon
                    draw_building_icon(self.map_surface, screen_x, screen_y, def_.appearance, self.viewport_zoom)

        # Show building legend if advanced map info is enabled
        if self.map_show_advanced_info:
            self.hud_surface.blit(
                self.building_legend_surface,
                (map_centre[0] + C.MAP_OVERLAY_SIZE/2 + 20, map_centre[1] - 180)
            )


        # Draw prohibited zones
        self.zone_overlay.fill((0, 0, 0, 0))
        for zone in self.game.env.prohibited_zones:
            # Calculate top-left corner in world coordinates
            zone_top_left_wld = zone.pos[0] - zone.dims[0] / 2, zone.pos[1] - zone.dims[1] / 2

            # Calculate screen position and dimensions
            screen_pos_x = (zone_top_left_wld[0] - viewport_top_left_x) / self.viewport_zoom
            screen_pos_z = (zone_top_left_wld[1] - viewport_top_left_z) / self.viewport_zoom
            screen_w = zone.dims[0] / self.viewport_zoom
            screen_h = zone.dims[1] / self.viewport_zoom

            zone_rect = pg.Rect(screen_pos_x, screen_pos_z, screen_w, screen_h)
            pg.draw.rect(self.zone_overlay, cols.MAP_PROHIBITED_FILL_COLOR, zone_rect)

        self.map_surface.blit(self.zone_overlay, (0, 0))

        for zone in self.game.env.prohibited_zones:
            zone_top_left_wld = zone.pos[0] - zone.dims[0] / 2, zone.pos[1] - zone.dims[1] / 2
            screen_pos_x = (zone_top_left_wld[0] - viewport_top_left_x) / self.viewport_zoom
            screen_pos_z = (zone_top_left_wld[1] - viewport_top_left_z) / self.viewport_zoom
            screen_w = zone.dims[0] / self.viewport_zoom
            screen_h = zone.dims[1] / self.viewport_zoom
            zone_rect = pg.Rect(screen_pos_x, screen_pos_z, screen_w, screen_h)

            pg.draw.rect(self.map_surface, cols.MAP_PROHIBITED_BORDER_COLOR, zone_rect, 2)

            if self.map_show_advanced_info:
                text_centre = (screen_pos_x + screen_w / 2, screen_pos_z + screen_h / 2)
                draw_text(self.map_surface, text_centre, 'centre', 'centre', zone.code, cols.MAP_PROHIBITED_TEXT_COLOUR, 20, self.fonts.monospaced)


        # Draw runways
        for runway in self.game.env.runways:
            # Convert runway world dimensions to map pixel dimensions, 1 pix min size
            runway_width_on_map = max(1, int(runway.w / self.viewport_zoom))
            runway_length_on_map = max(1, int(runway.l / self.viewport_zoom))

            # Calculate the runway's center position on the map_surface in pixels.
            runway_map_center_x = (runway.pos.x - viewport_top_left_x) / self.viewport_zoom
            runway_map_center_y = (runway.pos.z - viewport_top_left_z) / self.viewport_zoom

            # Skip if completely off-screen
            half_diag = 0.5 * math.hypot(runway_width_on_map, runway_length_on_map)
            if (runway_map_center_x + half_diag < 0
                or runway_map_center_x - half_diag > C.MAP_OVERLAY_SIZE
                or runway_map_center_y + half_diag < 0
                or runway_map_center_y - half_diag > C.MAP_OVERLAY_SIZE):
                continue

            # Create a base surface for the runway. Its length (l) will align with the Y-axis when unrotated.
            runway_surface_base = pg.Surface((runway_width_on_map, runway_length_on_map), pg.SRCALPHA)
            runway_surface_base.fill((cols.MAP_RUNWAY_COLOUR))

            rotated_runway_surface = pg.transform.rotate(runway_surface_base, -runway.heading)

            # Get bounding rectangle for the rotated surface and set its center.
            runway_rect_on_map = rotated_runway_surface.get_rect(center=(runway_map_center_x, runway_map_center_y))

            # Blit runway onto map surface
            self.map_surface.blit(rotated_runway_surface, runway_rect_on_map)

            runway_cx, runway_cy = runway_map_center_x, runway_map_center_y  # local alias

            # Show GPS pointer
            if runway is self.game.env.runways[self.gps_runway_index]:
                gps_rect = self.images.gps_dest_marker.get_rect(center=(runway_cx, runway_cy))
                self.map_surface.blit(self.images.gps_dest_marker, gps_rect)

            # Runway information
            draw_text(self.map_surface, (runway_cx, runway_cy - 50), 'centre', 'centre', runway.name, cols.WHITE, 20, self.fonts.monospaced)

            info_text = f"{runway.heading:03d}°, {units.convert_units(runway.pos.y, units.METRES, units.FEET):,.0f} ft"
            draw_text(self.map_surface, (runway_cx, runway_cy - 30), 'centre', 'centre', info_text, cols.WHITE, 15, self.fonts.monospaced)

        # Draw plane icon
        cx, cz = C.MAP_OVERLAY_SIZE/2, C.MAP_OVERLAY_SIZE/2
        icon_x = cx - (self.viewport_pos.x - self.plane.pos.x) / self.viewport_zoom
        icon_z = cz - (self.viewport_pos.z - self.plane.pos.z) / self.viewport_zoom

        plane_icon_rotated = pg.transform.rotate(self.images.plane_icon, -yaw)
        rotated_icon_rect = plane_icon_rotated.get_rect(center=(icon_x, icon_z))
        self.map_surface.blit(plane_icon_rotated, rotated_icon_rect)

        # Define scale bar size here as the world length is also used in grid rendering
        MAX_SCALE_BAR_SIZE = 80  # pixels
        target_size = self.viewport_zoom * MAX_SCALE_BAR_SIZE

        scale_bar_length_world = max([l for l in C.SCALE_BAR_LENGTHS if l <= target_size], default=C.SCALE_BAR_LENGTHS[0])

        # Show grid
        if self.map_show_advanced_info:
            GRID_MINOR_COL = (255, 255, 255, 80)
            GRID_MAJOR_COL = (255, 255, 255, 140)
            ORIGIN_POINT_COLOUR = (0, 255, 0)

            MINOR_INTERVAL = scale_bar_length_world
            MAJOR_INTERVAL = 5 * MINOR_INTERVAL

            self.grid_surface.fill((0, 0, 0, 0))
            if self.grid_detail_level != MINOR_INTERVAL:  # Clear label dicts when detail level changes
                self.grid_labels_x.clear()
                self.grid_labels_y.clear()
                self.grid_detail_level = MINOR_INTERVAL

            label_font = pg.font.Font(self.fonts.monospaced, 18)

            def world_to_map(world_x, world_z) -> tuple[float, float]:
                screen_x = (world_x - viewport_top_left_x) * (1/self.viewport_zoom)
                screen_y = (world_z - viewport_top_left_z) * (1/self.viewport_zoom)
                return screen_x, screen_y

            # Grid overlay bounds
            start_grid_x = int(viewport_top_left_x // MINOR_INTERVAL) * MINOR_INTERVAL
            end_grid_x = int((viewport_top_left_x + C.MAP_OVERLAY_SIZE * self.viewport_zoom) // MINOR_INTERVAL) * MINOR_INTERVAL + MINOR_INTERVAL
            start_grid_z = int(viewport_top_left_z // MINOR_INTERVAL) * MINOR_INTERVAL
            end_grid_z = int((viewport_top_left_z + C.MAP_OVERLAY_SIZE * self.viewport_zoom) // MINOR_INTERVAL) * MINOR_INTERVAL + MINOR_INTERVAL

            # Draw grid
            for world_x in range(start_grid_x, end_grid_x, MINOR_INTERVAL):
                p1 = world_to_map(world_x, viewport_top_left_z)
                p2 = world_to_map(world_x, viewport_top_left_z + C.MAP_OVERLAY_SIZE * self.viewport_zoom)
                pg.draw.line(self.grid_surface, GRID_MAJOR_COL if abs(world_x % MAJOR_INTERVAL) < C.MATH_EPSILON else GRID_MINOR_COL, p1, p2, 1)

                if abs(world_x % MAJOR_INTERVAL) <= C.MATH_EPSILON:
                    label_val = int(world_x)
                    label_surf = self.grid_labels_x.get(label_val)
                    if label_surf is None:
                        label_surf = label_font.render(f"{label_val:,.0f}", True, cols.WHITE)
                        self.grid_labels_x[label_val] = label_surf
                    label_rect = label_surf.get_rect(center=(p1[0], C.MAP_OVERLAY_SIZE - 15))
                    self.grid_surface.blit(label_surf, label_rect)

            for world_z in range(start_grid_z, end_grid_z, MINOR_INTERVAL):
                p1 = world_to_map(viewport_top_left_x, world_z)
                p2 = world_to_map(viewport_top_left_x + C.MAP_OVERLAY_SIZE * self.viewport_zoom, world_z)
                pg.draw.line(self.grid_surface, GRID_MAJOR_COL if abs(world_z % MAJOR_INTERVAL) < C.MATH_EPSILON else GRID_MINOR_COL, p1, p2, 1)

                if abs(world_z % MAJOR_INTERVAL) <= C.MATH_EPSILON:
                    label_val = int(world_z)
                    label_surf = self.grid_labels_y.get(label_val)
                    if label_surf is None:
                        label_surf = label_font.render(f"{label_val:,.0f}", True, cols.WHITE)
                        self.grid_labels_y[label_val] = label_surf
                    label_rect = label_surf.get_rect()
                    label_rect.left = 5
                    label_rect.centery = int(p1[1])
                    self.grid_surface.blit(label_surf, label_rect)

            # Draw origin
            origin_map_x, origin_map_y = world_to_map(0, 0)
            if 0 <= origin_map_x <= C.MAP_OVERLAY_SIZE and 0 <= origin_map_y <= C.MAP_OVERLAY_SIZE:
                pg.draw.circle(self.grid_surface, ORIGIN_POINT_COLOUR, (origin_map_x, origin_map_y), 5)

            # Blit grid surface onto map surface
            self.map_surface.blit(self.grid_surface, (0, 0))

        # North indicator - draw an arrow pointing upwards
        north_indicator_size = 20
        north_indicator_offset_x = 12
        north_indicator_offset_y = 42
        ni_center_x = north_indicator_offset_x + north_indicator_size // 2
        ni_center_y = north_indicator_offset_y + north_indicator_size // 2

        # Calculate arrow vertices
        arrow_points = [
            (ni_center_x, north_indicator_offset_y),  # Top point
            (ni_center_x - north_indicator_size // 4, ni_center_y + north_indicator_size // 2),  # Bottom-left
            (ni_center_x, ni_center_y + north_indicator_size // 4),  # Bottom-middle (for dart shape)
            (ni_center_x + north_indicator_size // 4, ni_center_y + north_indicator_size // 2),  # Bottom-right
        ]
        pg.draw.polygon(self.map_surface, cols.WHITE, arrow_points)
        draw_text(self.map_surface, (ni_center_x, ni_center_y - north_indicator_offset_y), 'centre', 'top', "N", cols.WHITE, 25, self.fonts.monospaced)

        # Draw scale bar
        scale_bar_offset = (12, 80)

        scale_bar_length_pix = scale_bar_length_world / self.viewport_zoom
        scale_bar_rect = pg.Rect(scale_bar_offset[0], scale_bar_offset[1], scale_bar_length_pix, 5)

        pg.draw.rect(self.map_surface, cols.WHITE, scale_bar_rect)
        draw_text(self.map_surface, (scale_bar_offset[0], scale_bar_offset[1] + 20), 'left', 'centre', f"{scale_bar_length_world:,} m", cols.WHITE, 20, self.fonts.monospaced)

        # Calculate ground speed
        ground_speed_vec = pg.Vector3(self.plane.vel.x, 0, self.plane.vel.z)
        ground_speed_mag = ground_speed_vec.length()

        draw_text(self.map_surface, (C.MAP_OVERLAY_SIZE//2 - 100, 30), 'left', 'centre', 'GS', (100, 255, 255), 25, self.fonts.monospaced)
        draw_text(self.map_surface, (C.MAP_OVERLAY_SIZE//2 - 45, 30), 'left', 'centre', f"{units.convert_units(ground_speed_mag, units.METRES/units.SECONDS, units.KNOTS):,.0f}", cols.WHITE, 25, self.fonts.monospaced)

        # Calculate ETA
        dest_runway = self.game.env.runways[self.gps_runway_index]

        # Take out vertical components of relevant vectors
        dest_pos_flat = pg.Vector3(dest_runway.pos.x, 0, dest_runway.pos.z)
        plane_pos_flat = pg.Vector3(self.plane.pos.x, 0, self.plane.pos.z)
        vel_flat = pg.Vector3(self.plane.vel.x, 0, self.plane.vel.z)

        vec_to_dest = dest_pos_flat - plane_pos_flat
        distance = vec_to_dest.length()

        if distance <= C.MATH_EPSILON:
            # Very small distance -> already at destination
            eta_seconds = 0
        else:
            direction = vec_to_dest.normalize()
            ground_speed_towards_dest = vel_flat.dot(direction)

            eta_seconds: float | None
            if ground_speed_towards_dest <= C.MATH_EPSILON:
                eta_seconds = None
            else:
                eta_seconds = distance / ground_speed_towards_dest

        if eta_seconds is None:
            eta_text = "--:--"
        elif eta_seconds >= 3_600:
            eta_text = "59:59+"
        else:
            eta_seconds_rounded = int(eta_seconds)

            eta_text_mins = eta_seconds_rounded // 60
            eta_text_secs = eta_seconds_rounded % 60

            eta_text = f"{eta_text_mins:02d}:{eta_text_secs:02d}"

        draw_text(self.map_surface, (C.MAP_OVERLAY_SIZE//2 - 100, 55), 'left', 'centre', 'ETA', (100, 255, 255), 25, self.fonts.monospaced)
        draw_text(self.map_surface, (C.MAP_OVERLAY_SIZE//2 - 45, 55), 'left', 'centre', eta_text, cols.WHITE, 25, self.fonts.monospaced)

        # Blit the completed map to the main HUD surface
        map_rect = self.map_surface.get_rect(center=(map_centre))
        self.hud_surface.blit(self.map_surface, map_rect)

        # Show height key
        if self.map_show_advanced_info:
            self.hud_surface.blit(
                self.height_legend_surface,
                (C.WN_W//2 - C.MAP_OVERLAY_SIZE//2 - 200, map_centre[1] - 180)
            )

    def draw_pause_screen(self) -> None:
        for button in (
            self.continue_button, self.restart_button,
            self.menu_button, self.help_button, self.controls_button
        ):
            button.draw(self.hud_surface)

        draw_text(
            self.hud_surface, (C.WN_W//2, C.WN_H*0.35), 'centre', 'centre',
            'Game Paused', (255, 255, 255), 50, self.fonts.monospaced
        )

    def draw_confirmation_menu(self) -> None:
        if self.in_menu_confirmation or self.in_restart_confirmation:
            draw_transparent_rect(
                self.hud_surface, (C.WN_W//2 - 400, C.WN_H//2 - 175), (800, C.WN_H*0.3),
                border_thickness=3
            )

            draw_text(
                self.hud_surface, (C.WN_W//2, C.WN_H*0.4), 'centre', 'centre',
                'Are you sure?', (255, 255, 255), 50, self.fonts.monospaced
            )

            for button in (self.yes_button, self.no_button):
                button.draw(self.hud_surface)

    def draw_controls_screen(self) -> None:
        self.back_button.draw(self.hud_surface)

        controls_sections: dict[ControlsSectionID, ControlsSection] = self.game.assets.texts.controls_sections  # Local alias

        draw_transparent_rect(
            self.hud_surface, (C.WN_W * 0.1, C.WN_H * 0.1), (C.WN_W * 0.8, C.WN_H*0.70),
            border_thickness=3
        )

        draw_text(
            self.hud_surface, (C.WN_W//2, C.WN_H*0.16), 'centre', 'centre',
            'Controls', (255, 255, 255), 50, self.fonts.monospaced
        )

        draw_text(self.hud_surface, (C.WN_W//2 - 480, C.WN_H*0.3), 'left', 'centre', ControlsSectionID.MAIN, (0, 192, 255), 40, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.MAIN].keys.items()):
            draw_text(self.hud_surface, (C.WN_W//2 - 480, C.WN_H * (0.38 + 0.04*i)), 'left', 'centre', key, (150, 230, 255), 27, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2 - 360, C.WN_H * (0.38 + 0.04*i)), 'left', 'centre', action, cols.WHITE, 27, self.fonts.monospaced)

        draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H*0.26), 'left', 'centre', ControlsSectionID.DISPLAYS, (0, 192, 255), 25, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.DISPLAYS].keys.items()):
            draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H * (0.31 + 0.03*i)), 'left', 'centre', key, (150, 230, 255), 21, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2 + 140, C.WN_H * (0.31 + 0.03*i)), 'left', 'centre', action, cols.WHITE, 21, self.fonts.monospaced)

        draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H*0.4), 'left', 'centre', ControlsSectionID.MAP, (0, 192, 255), 25, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.MAP].keys.items()):
            draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H * (0.45 + 0.03*i)), 'left', 'centre', key, (150, 230, 255), 21, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2 + 140, C.WN_H * (0.45 + 0.03*i)), 'left', 'centre', action, cols.WHITE, 21, self.fonts.monospaced)
        note = controls_sections[ControlsSectionID.MAP].note
        assert note is not None
        draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H * (0.45 + 0.03 * (len(controls_sections[ControlsSectionID.MAP].keys) + 0.5))), 'left', 'centre', note, (255, 255, 255), 21, self.fonts.monospaced)

        draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H*0.64), 'left', 'centre', ControlsSectionID.UTILITIES, (0, 192, 255), 25, self.fonts.monospaced)
        for i, (key, action) in enumerate(controls_sections[ControlsSectionID.UTILITIES].keys.items()):
            draw_text(self.hud_surface, (C.WN_W//2 + 20, C.WN_H * (0.69 + 0.03*i)), 'left', 'centre', key, (150, 230, 255), 21, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2 + 140, C.WN_H * (0.69 + 0.03*i)), 'left', 'centre', action, cols.WHITE, 21, self.fonts.monospaced)

    def draw_help_screen(self) -> None:
        draw_transparent_rect(
            self.hud_surface, (30, 30), (C.WN_W - 60, C.WN_H - 60), border_thickness=3
        )

        rect = self.images.logo.get_rect(center=(C.WN_W//2, 100))
        self.hud_surface.blit(self.images.logo, rect)
        draw_text(
            self.hud_surface, (rect.centerx, rect.bottom + 8), 'centre', 'top',
            "Help", (0, 192, 255), 36, self.fonts.monospaced
        )

        self.back_button.draw(self.hud_surface)

        left = 80
        top = rect.bottom + 80
        bottom = C.WN_H - 120
        width = C.WN_W - 320
        logical_y = top
        indent_px = 24
        scrollbar_w = 12
        scrollbar_x = left + width + 20

        visual_styles: dict[FLine.Style, tuple[int, Colour, bool]] = {
            FLine.Style.HEADING_1: (36, (0, 192, 255), False),
            FLine.Style.HEADING_2: (28, (0, 192, 255), False),
            FLine.Style.BULLET: (24, cols.WHITE, True),
            FLine.Style.NORMAL: (24, cols.WHITE, False),
        }

        for fline in self.game.assets.texts.help_lines:
            size, colour, bullet = visual_styles[fline.style]

            x = left + indent_px * fline.indent
            max_w = width - indent_px * fline.indent

            font = pg.font.Font(self.fonts.monospaced, size)
            if bullet:
                bullet_prefix = "• "
                prefix_w = font.size(bullet_prefix)[0]
                wrapped = wrap_text(fline.text, max_w - prefix_w, font)
                for i, line in enumerate(wrapped):
                    render_y = logical_y - self.help_screen_offset
                    if render_y + font.get_linesize() >= top and render_y <= bottom:
                        if i == 0:
                            draw_text(self.hud_surface, (x, render_y), 'left', 'top', bullet_prefix, colour, size, font)
                        draw_text(self.hud_surface, (x + prefix_w, render_y), 'left', 'top', line, colour, size, font)
                    logical_y += font.get_linesize() + 4
            else:
                for line in wrap_text(fline.text, max_w, font):
                    render_y = logical_y - self.help_screen_offset
                    if render_y + font.get_linesize() >= top and render_y <= bottom:
                        draw_text(self.hud_surface, (x, render_y), 'left', 'top', line, colour, size, font)
                    logical_y += font.get_linesize() + 4

            logical_y += 6  # extra spacing between FLine entries

        content_height = max(0, logical_y - top)
        view_height = max(0, bottom - top)
        self.help_max_offset = max(0, content_height - view_height)
        self.help_screen_offset = max(0, min(self.help_screen_offset, self.help_max_offset))

        scrollbar_h = max(0, bottom - top)
        bar_bg = pg.Rect(scrollbar_x, top, scrollbar_w, scrollbar_h)
        pg.draw.rect(self.hud_surface, (55, 55, 55), bar_bg)

        if content_height > 0:
            if self.help_max_offset == 0:
                thumb_h = scrollbar_h
                thumb_y = top
            else:
                thumb_h = max(24, int(scrollbar_h * (view_height / content_height)))
                max_thumb_y = top + scrollbar_h - thumb_h
                thumb_y = top + int((self.help_screen_offset / self.help_max_offset) * (max_thumb_y - top))

            thumb = pg.Rect(scrollbar_x, thumb_y, scrollbar_w, thumb_h)
            pg.draw.rect(self.hud_surface, (185, 185, 185), thumb)

    def draw_hud(self):

        self.hud_surface.fill((0, 0, 0, 0))  # clear with transparency

        # Show cockpit if cockpit is enabled
        # Always show cockpit if the plane has crashed
        if self.show_cockpit or self.plane.crashed:
            self.cockpit_renderer.draw(self.hud_surface, self.warn_stall, self.warn_overspeed)

        # Render map
        if self.map_up:
            self.draw_map()

        # Render jukebox
        if self.jukebox_menu_up:
            self.draw_jukebox_menu()

        # Render controls quick reference
        if self.controls_quick_ref_up:
            w, _ = self.controls_quick_ref_surface.get_size()
            self.hud_surface.blit(self.controls_quick_ref_surface, (int(C.WN_W - (w + 30) * self.controls_quick_ref_up), 50))  # centred when fully active

        self.cockpit_renderer.draw_crash_flash(self.hud_surface)

        # Exit controls
        if self.time_elapsed < 5_000 or not self.plane.flyable:
            draw_text(self.hud_surface, (15, 30), 'left', 'centre', "Press Esc to pause", cols.WHITE, 30, self.fonts.monospaced)

        # Show dialog box
        if self.dialog_box.active_time:
            text_size = 30

            text_length = len(self.dialog_box.msg)
            text_length_pix = text_length * text_size/2

            buffer = text_size * 0.7

            draw_transparent_rect(
                self.hud_surface, (C.WN_W//2 - text_length_pix/2 - buffer, C.WN_H*0.2 - text_size*1.2), (text_length_pix + 2*buffer, text_size*2.4), (0, 0, 0, 180), 2
            )
            draw_text(
                self.hud_surface, (C.WN_W//2, C.WN_H*0.2), 'centre', 'centre',
                self.dialog_box.msg, self.dialog_box.colour, text_size, self.fonts.monospaced
            )

        def show_crash_reason(reason: CrashReason) -> None:
            if reason == CrashReason.TERRAIN:
                ui_text = "COLLISION WITH TERRAIN"
            elif reason == CrashReason.OCEAN:
                ui_text = "COLLISION WITH OCEAN"
            elif reason == CrashReason.OBSTACLE:
                ui_text = "COLLISION WITH OBSTACLE"
            elif reason == CrashReason.RUNWAY:
                ui_text = "IMPROPER LANDING ON RUNWAY"

            draw_transparent_rect(
                self.hud_surface, (C.WN_W*0.28, C.WN_H*0.3), (C.WN_W*0.44, C.WN_H*0.3),
                (0, 0, 0, 180), 2
            )
            draw_text(self.hud_surface, (C.WN_W//2, C.WN_H*0.37), 'centre', 'centre', 'CRASH', (255, 0, 0), 50, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2, C.WN_H*0.45), 'centre', 'centre', ui_text, cols.WHITE, 30, self.fonts.monospaced)

        # Show crash reason on screen
        if self.plane.crash_reason is not None:
            show_crash_reason(self.plane.crash_reason)
            self.crash_screen_restart_button.draw(self.hud_surface)

        # If paused, show overlay
        if self.paused:
            # Always show transparent dark overlay
            transparent_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
            transparent_surface.fill((0, 0, 0, 100))
            self.hud_surface.blit(transparent_surface, (0, 0))

            if self.in_controls_screen:
                self.draw_controls_screen()
            elif self.in_help_screen:
                self.draw_help_screen()
            else:
                self.draw_pause_screen()

        self.draw_confirmation_menu()  # always show confirmation menu if one is active

        # Upload HUD surface to OpenGL
        hud_data = pg.image.tostring(self.hud_surface, "RGBA", True)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.hud_tex)
        gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, C.WN_W, C.WN_H, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, hud_data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        gl.glDisable(gl.GL_DEPTH_TEST)

        # Render HUD on top of 3D world
        gl.glEnable(gl.GL_TEXTURE_2D)

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.hud_tex)
        gl.glColor4f(1, 1, 1, 1)

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glOrtho(0, C.WN_W, C.WN_H, 0, -1, 1)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()

        gl.glBegin(gl.GL_QUADS)

        gl.glTexCoord2f(0, 1); gl.glVertex2f(0, 0)
        gl.glTexCoord2f(1, 1); gl.glVertex2f(C.WN_W, 0)
        gl.glTexCoord2f(1, 0); gl.glVertex2f(C.WN_W, C.WN_H)
        gl.glTexCoord2f(0, 0); gl.glVertex2f(0, C.WN_H)
        gl.glEnd()

        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_TEXTURE_2D)

    def draw_jukebox_menu(self) -> None:
        # Clear jukebox menu surface
        self.jukebox_menu_surface.fill((0, 0, 0, 0))
        draw_transparent_rect(self.jukebox_menu_surface, (0, 0), (540, 600), (0, 0, 0, 150), 2)

        draw_text(
            self.jukebox_menu_surface, (270, 48), 'centre', 'centre',
            "Jukebox", cols.WHITE, 35, self.fonts.monospaced
        )

        for i, (key, desc) in enumerate(self.game.assets.texts.controls_sections[ControlsSectionID.JUKEBOX].keys.items()):
            draw_text(
                self.jukebox_menu_surface, (16, 95 + 25 * i), 'left', 'centre',
                key, cols.BLUE, 18, self.fonts.monospaced
            )
            draw_text(
                self.jukebox_menu_surface, (96, 95 + 25 * i), 'left', 'centre',
                desc, cols.WHITE, 18, self.fonts.monospaced
            )

        ...

        self.hud_surface.blit(self.jukebox_menu_surface, (C.WN_W/2 - 270, C.WN_H - (C.WN_H / 2 + 300) * self.jukebox_menu_up))

    def update(self, dt: int):
        assert self.game.env is not None
        assert self.game.env.prohibited_zones is not None

        self._frame_count += 1
        self.time_elapsed += dt

        self.sun.update()
        self.moon.update()

        if self.paused:
            return

        self.dialog_box.update(dt)

        if self.plane.crashed:
            self.smoke_manager.update(dt)
            self.plane.increment_crash_timer(dt)

            self.dialog_box.reset()

            self.channel_stall.stop()
            self.channel_overspeed.stop()

            self.channel_wind.stop()
            self.channel_engine_active.stop()
            self.channel_engine_ambient.stop()

            self.channel_scrape.stop()

            return

        if self.auto_screenshots_enabled:
            self._auto_screenshot_elapsed_ms += dt
            if self._auto_screenshot_elapsed_ms >= self.auto_screenshot_interval_ms:
                self._auto_screenshot_pending = True
                self._auto_screenshot_elapsed_ms %= self.auto_screenshot_interval_ms

        # Jukebox menu update
        if self.jukebox_menu_state == Visibility.HIDDEN:
            self.jukebox_menu_up -= (dt/1000) / C.JUKEBOX_MENU_TOGGLE_ANIMATION_DURATION
        else:
            self.jukebox_menu_up += (dt/1000) / C.JUKEBOX_MENU_TOGGLE_ANIMATION_DURATION
        self.jukebox_menu_up = clamp(self.jukebox_menu_up, (0, 1))

        # Map update
        if self.map_state == Visibility.HIDDEN:
            self.map_up -= (dt/1000) / C.MAP_TOGGLE_ANIMATION_DURATION
        else:
            self.map_up += (dt/1000) / C.MAP_TOGGLE_ANIMATION_DURATION
        self.map_up = clamp(self.map_up, (0, 1))

        # Controls ref update
        if self.controls_quick_ref_state == Visibility.HIDDEN:
            self.controls_quick_ref_up -= (dt/1000) / C.CONTROLS_REF_TOGGLE_ANIMATION_DURATION
        else:
            self.controls_quick_ref_up += (dt/1000) / C.CONTROLS_REF_TOGGLE_ANIMATION_DURATION
        self.controls_quick_ref_up = clamp(self.controls_quick_ref_up, (0, 1))

        self.plane.update(dt)

        # Stall warning
        self.warn_stall = self.plane.stalled
        if self.warn_stall:
            if not self.channel_stall.get_busy():
                self.channel_stall.play(self.sounds.stall_warning, loops=-1)
        else:
            self.channel_stall.stop()

        # Overspeed warning
        self.warn_overspeed = self.plane.vel.length() > self.plane.model.v_ne  # Both in m/s
        if self.warn_overspeed:
            if not self.channel_overspeed.get_busy():
                self.channel_overspeed.play(self.sounds.overspeed, loops=-1)
        else:
            self.channel_overspeed.stop()

        # Update engine and wind sounds
        if not self.channel_wind.get_busy():
            self.channel_wind.play(self.sounds.wind, loops=-1)
        if not self.channel_engine_ambient.get_busy():
            self.channel_engine_ambient.play(self.sounds.engine_loop_ambient, loops=-1)
        if not self.channel_engine_active.get_busy():
            self.channel_engine_active.play(self.sounds.engine_loop_active, loops=-1)

        wind_sound_strength = (self.plane.vel.length() - 61.73) / 25.72  # start wind at 120 kn, full at 170
        self.channel_wind.set_volume(clamp(wind_sound_strength, (0, 1)))

        throttle_sound_strength = self.plane.throttle_frac ** 1.8
        self.channel_engine_active.set_volume(throttle_sound_strength)

        # Terrain scrape sound
        if (not self.plane.over_runway) and self.plane.on_ground:
            if not self.channel_scrape.get_busy():
                self.channel_scrape.play(self.sounds.terrain_scrape, -1)
        else:
            self.channel_scrape.stop()

        # Prohibited zone warning
        self.show_prohibited_zone_warning = self.plane.over_prohibited_zone()
        if self.show_prohibited_zone_warning:
            if not self.channel_prohibited.get_busy():
                self.channel_prohibited.play(self.sounds.prohibited_zone_warning, loops=-1)
            self.dialog_box.set_message("Immediately exit this zone - penalties may apply", (255, 127, 0), 100)
        else:
            self.channel_prohibited.stop()

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        # Screenshot - this needs to ALWAYS WORK
        if self.pressed(keys, pg.K_F5):
            self.take_screenshot()

        # Meta controls
        if self.pressed(keys, pg.K_ESCAPE):
            if self.in_controls_screen or self.in_help_screen:
                self.in_controls_screen = False
                self.in_help_screen = False
                self.help_screen_offset = 0
                self.help_scroll_vel = 0
            else:
                self.paused = not self.paused

            self.channel_wind.stop()
            self.channel_engine_active.stop()
            self.channel_engine_ambient.stop()

            self.channel_scrape.stop()

        if self.paused and not (self.in_menu_confirmation or self.in_restart_confirmation):
            if self.controls_button.check_click(events) and not self.in_controls_screen and not self.in_help_screen:
                self.in_controls_screen = True
                self.in_help_screen = False
            elif self.help_button.check_click(events) and not self.in_controls_screen and not self.in_help_screen:
                self.in_help_screen = True
                self.in_controls_screen = False
            elif self.back_button.check_click(events) and (self.in_controls_screen or self.in_help_screen):
                self.in_controls_screen = False
                self.in_help_screen = False
                self.help_screen_offset = 0.0
                self.help_scroll_vel = 0.0

            if self.in_help_screen:
                scroll_accel = 0.004 * dt
                wheel_impulse = 25

                for event in events:
                    if event.type == pg.MOUSEWHEEL:
                        self.help_scroll_vel -= event.y * wheel_impulse

                if keys[pg.K_UP]:
                    self.help_scroll_vel -= scroll_accel
                if keys[pg.K_DOWN]:
                    self.help_scroll_vel += scroll_accel
                if self.pressed(keys, pg.K_PAGEUP):
                    self.help_scroll_vel -= 220
                if self.pressed(keys, pg.K_PAGEDOWN):
                    self.help_scroll_vel += 220

                self.help_screen_offset += self.help_scroll_vel

                self.help_scroll_vel *= 0.85
                if abs(self.help_scroll_vel) < 0.02:
                    self.help_scroll_vel = 0.0

                if self.help_screen_offset < 0:
                    self.help_screen_offset = 0
                    self.help_scroll_vel = 0.0
                elif self.help_screen_offset > self.help_max_offset:
                    self.help_screen_offset = self.help_max_offset
                    self.help_scroll_vel = 0.0

            if self.continue_button.check_click(events):
                self.paused = False

            if self.restart_button.check_click(events):
                self.in_restart_confirmation = True

            if self.menu_button.check_click(events):
                self.in_menu_confirmation = True

            self.update_prev_keys(keys); return

        if self.in_menu_confirmation:
            if self.yes_button.check_click(events):
                self.game.enter_state(StateID.TITLE)

            if self.no_button.check_click(events):
                self.in_menu_confirmation = False

        if self.in_restart_confirmation:
            if self.yes_button.check_click(events):
                self.reset()

            if self.no_button.check_click(events):
                self.in_restart_confirmation = False

        # Toggle jukebox menu
        if self.pressed(keys, pg.K_j):
            self.jukebox_menu_state = Visibility.toggle(self.jukebox_menu_state)

        # Cockpit visibility toggling
        if self.pressed(keys, pg.K_F1):  # F1 to toggle HUD
            self.show_cockpit = not self.show_cockpit

        # Block flight controls if crashed or disabled
        if not self.plane.flyable:
            if self.crash_screen_restart_button.check_click(events):
                self.in_restart_confirmation = True

            self.update_prev_keys(keys)
            return

        # Show/hide map
        if self.pressed(keys, pg.K_m):
            self.map_state = Visibility.toggle(self.map_state)

        # Show/hide quick ref for controls
        if self.pressed(keys, pg.K_o):
            self.controls_quick_ref_state = Visibility.toggle(self.controls_quick_ref_state)

        # Cycle GPS waypoint
        if self.pressed(keys, pg.K_g):
            self.plane.cycle_gps_waypoint()

        if self.map_state == Visibility.SHOWN:
            # While map is shown: control zoom
            if keys[pg.K_w]:
                self.viewport_zoom /= 2.5 ** (dt/1000)
            if keys[pg.K_s]:
                self.viewport_zoom *= 2.5 ** (dt/1000)
            self.viewport_zoom = clamp(self.viewport_zoom, (C.MAP_ZOOM_MIN, C.MAP_ZOOM_MAX))
        else:
            # Throttle controls
            if keys[pg.K_w]:
                self.plane.throttle_frac += C.THROTTLE_SPEED * dt/1000
            if keys[pg.K_s]:
                self.plane.throttle_frac -= C.THROTTLE_SPEED * dt/1000
            self.plane.throttle_frac = clamp(self.plane.throttle_frac, (0, 1))

        self.map_show_advanced_info = self.map_state == Visibility.SHOWN and keys[pg.K_h]

        # Turning or map panning
        if self.map_state == Visibility.SHOWN:
            self.plane.rot_input_container.reset()  # zero out plane rotation inputs while map is shown
            panning_speed = self.viewport_zoom * 150

            # Map shown -> pan map
            if keys[pg.K_UP]:
                self.viewport_pos.z -= panning_speed * dt/1000
                self.viewport_auto_panning = False
            if keys[pg.K_DOWN]:
                self.viewport_pos.z += panning_speed * dt/1000
                self.viewport_auto_panning = False
            if keys[pg.K_LEFT]:
                self.viewport_pos.x -= panning_speed * dt/1000
                self.viewport_auto_panning = False
            if keys[pg.K_RIGHT]:
                self.viewport_pos.x += panning_speed * dt/1000
                self.viewport_auto_panning = False

            # Reset map viewport pos
            if self.pressed(keys, pg.K_SPACE):
                self.viewport_pos = self.plane.pos.copy()
                self.viewport_auto_panning = True
        else:
            # Reset map viewport pos once map goes fully down
            if not self.map_up:
                self.viewport_pos = self.plane.pos.copy()
                self.viewport_auto_panning = True

            # Pitch
            direction: Literal[-1, 1] = -1 if self.game.save_data.invert_y_axis else 1

            pitch_input = 0  # temporary container
            if keys[pg.K_UP]:
                pitch_input += direction
            if keys[pg.K_DOWN]:
                pitch_input -= direction
            assert pitch_input in (-1, 0, 1)
            self.plane.rot_input_container.pitch_input = pitch_input

            # Turning
            roll_input = 0  # temporary container
            if keys[pg.K_LEFT]:
                roll_input -= 1
            if keys[pg.K_RIGHT]:
                roll_input += 1
            assert roll_input in (-1, 0, 1)
            self.plane.rot_input_container.roll_input = roll_input

        # Flaps
        if keys[pg.K_z]:  # Flaps up
            self.plane.flaps += C.FLAPS_SPEED * dt/1000
        if keys[pg.K_x]:  # Flaps down
            self.plane.flaps -= C.FLAPS_SPEED * dt/1000
        self.plane.flaps = clamp(self.plane.flaps, (0, 1))

        # Rudder
        if keys[pg.K_a]:
            self.plane.rudder -= C.RUDDER_SPEED * dt/1000 * min(1, self.plane.vel.length() / 10)
        if keys[pg.K_d]:
            self.plane.rudder += C.RUDDER_SPEED * dt/1000 * min(1, self.plane.vel.length() / 10)
        if not (keys[pg.K_a] or keys[pg.K_d]):
            one_minus_decay = (1 - C.RUDDER_SNAPBACK) ** (dt/1000)
            self.plane.rudder *= one_minus_decay
        self.plane.rudder = clamp(self.plane.rudder, (-1, 1))

        # Brakes
        self.plane.braking = keys[pg.K_b]  # b to brake

        self.update_prev_keys(keys)

    def draw(self, wn: Surface):
        assert self.game.env is not None
        assert self.game.config_presets is not None

        colour_scheme = sky_colour_from_hour(fetch_hour())

        gl.glClear(cast(int, gl.GL_COLOR_BUFFER_BIT) | cast(int, gl.GL_DEPTH_BUFFER_BIT))

        # Draw sky gradient background
        self.sky.draw(colour_scheme)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        # Apply camera transformations based on plane's state
        # The order of operations is Yaw, then Pitch, then Roll.
        # OpenGL applies matrix transformations in reverse order of the calls.
        pitch, yaw, roll = self.plane.get_rot()
        gl.glRotatef(roll, 0, 0, 1) # 3. Roll
        gl.glRotatef(pitch, 1, 0, 0) # 2. Pitch
        gl.glRotatef(yaw, 0, 1, 0) # 1. Yaw

        camera_y = self.plane.pos.y + C.CAMERA_RADIUS
        gl.glTranslatef(-self.plane.pos.x, -camera_y, -self.plane.pos.z)

        camera_fwd = self.plane.native_fwd  # now uses native fwd vector, so no need to recalculate

        self.draw_stars()

        self.sun.draw()
        self.moon.draw()

        cloud_attenuation = 1.0
        for layer in self.game.config_presets.cloud_configs[self.game.save_data.cloud_config_idx].layers:
            cloud_attenuation *= (1 - layer.coverage * 0.2)

        self.ground.draw(cloud_attenuation)
        self.ocean.draw(cloud_attenuation)

        for runway in self.game.env.runways:
            runway.draw(cloud_attenuation)

        cloud_layers = self.game.config_presets.cloud_configs[self.game.save_data.cloud_config_idx]
        for cloud_layer in cloud_layers.layers:
            cloud_layer.draw(self.plane.pos, camera_fwd)

        self.draw_buildings(cloud_attenuation)

        if self.auto_screenshots_enabled and self._auto_screenshot_pending:
            self._auto_screenshot_pending = False
            self.take_screenshot(notify=True)

        self.draw_hud()
