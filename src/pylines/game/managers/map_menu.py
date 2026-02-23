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

from typing import TYPE_CHECKING, cast

import pygame as pg

from pylines.core.custom_types import Surface
import pylines.core.colours as cols
from pylines.game.managers.pop_up_menus import PopupMenu
import pylines.core.constants as C
from pylines.core.utils import draw_text
import pylines.core.units as units

import math
from typing import TYPE_CHECKING, Callable, cast

import numpy as np
import pygame as pg

import pylines.core.colours as cols
import pylines.core.constants as C
from pylines.core.paths import DIRECTORIES
from pylines.core.custom_types import Colour, RealNumber
from pylines.core.utils import (
    draw_text
)
from pylines.objects.buildings import (
    BuildingDefinition,
    BuildingMapIconType,
    draw_building_icon,
)

if TYPE_CHECKING:
    from pylines.game.game import Game
    from pylines.objects.objects import Plane


class MapMenu(PopupMenu):
    def __init__(self, game: Game, plane: Plane) -> None:
        super().__init__(game)
        self.plane = plane
        self.viewport_pos: pg.Vector3 = self.plane.pos.copy()
        self.viewport_auto_panning: bool = True

        # Cached surface
        self.surface: Surface = pg.Surface((C.MAP_OVERLAY_SIZE, C.MAP_OVERLAY_SIZE), pg.SRCALPHA)

        # Surface to which to draw prohibited zones before blitting to a main HUD surface
        self.zone_overlay = pg.Surface((C.MAP_OVERLAY_SIZE, C.MAP_OVERLAY_SIZE), pg.SRCALPHA)
        self.zone_overlay.fill((0, 0, 0, 0))

        # Grid for advanced map info
        self.grid_surface = pg.Surface((C.MAP_OVERLAY_SIZE, C.MAP_OVERLAY_SIZE), pg.SRCALPHA)
        self.grid_surface.fill((0, 0, 0, 0))

        # Cache numeric grid labels to avoid wasteful text redraws
        self.grid_labels_x: dict[int, pg.Surface] = {}  # value, surface
        self.grid_labels_y: dict[int, pg.Surface] = {}  # value, surface
        self.grid_detail_level: int | None = None

        self.build()

    def generate_building_legend(self) -> Surface:
        assert self.game.env is not None

        width, height = 200, 360
        surf = pg.Surface((width, height), pg.SRCALPHA)
        surf.fill((0, 0, 0, 180))
        pg.draw.rect(surf, cols.MAP_BORDER_COLOUR, surf.get_rect(), 2)

        draw_text(surf, (100, 25), 'centre', 'centre', "Buildings", cols.WHITE, 20, self.game.assets.fonts.monospaced)

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
            draw_text(surf, (75, screen_y), 'left', 'centre', f"{def_.common_name}", cols.WHITE, 15, self.game.assets.fonts.monospaced)
            draw_building_icon(surf, 35, screen_y, def_.appearance)

            curr_h = icon_height(def_)
            next_h = icon_height(items[idx + 1][1]) if idx + 1 < len(items) else 0
            line_h = max(15, 15 + curr_h//2 + next_h//2)
            screen_y += line_h

        return surf

    def generate_height_legend(self) -> Surface:
        width, height = 180, 360
        surf = pg.Surface((width, height), pg.SRCALPHA)
        surf.fill((0, 0, 0, 180))
        pg.draw.rect(surf, cols.MAP_BORDER_COLOUR, surf.get_rect(), 2)

        draw_text(surf, (90, 25), 'centre', 'centre', "Altitude (ft)", cols.WHITE, 20, self.game.assets.fonts.monospaced)
        surf.blit(self.height_key, (105, 55))

        for h in range(-12_000, 18_001, 2_000):
            text_y = 55 + (self.HEIGHT_KEY_H * (1 - ((h + 12_000) / 30_000)))
            draw_text(surf, (100, text_y), 'right', 'centre', f"{h:,.0f}", cols.WHITE, 15, self.game.assets.fonts.monospaced)

        return surf

    def build(self):
        assert self.game.env is not None

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

        self.viewport_zoom: float = 50  # metres per pixel of map shown
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

        self.building_legend_surface = self.generate_building_legend()
        self.height_legend_surface = self.generate_height_legend()

    def draw(self, surface: Surface, show_advanced_info: bool) -> None:
        assert self.game.env is not None

        _, yaw, _ = self.plane.get_rot()

        self.surface.fill((0, 0, 0, 255))
        NUM_TILES = math.ceil(C.HALF_WORLD_SIZE*2 / (C.METRES_PER_TILE))

        if self.viewport_auto_panning:
            self.viewport_pos = self.plane.pos.copy()

        px, _, pz = self.viewport_pos

        # Render base map
        map_centre = C.WN_W//2, int(285 + C.WN_H * (1 - self.state.animation_openness))

        # Map border
        outer_map_rect = pg.Rect(0, 0, C.MAP_OVERLAY_SIZE+10, C.MAP_OVERLAY_SIZE+10)
        outer_map_rect.center = map_centre
        pg.draw.rect(surface, cols.MAP_BORDER_COLOUR, outer_map_rect)

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
                self.surface.blit(scaled_tile, dest_rect)


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
                    draw_building_icon(self.surface, screen_x, screen_y, def_.appearance, self.viewport_zoom)

        # Show building legend if advanced map info is enabled
        if show_advanced_info:
            surface.blit(
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

        self.surface.blit(self.zone_overlay, (0, 0))

        for zone in self.game.env.prohibited_zones:
            zone_top_left_wld = zone.pos[0] - zone.dims[0] / 2, zone.pos[1] - zone.dims[1] / 2
            screen_pos_x = (zone_top_left_wld[0] - viewport_top_left_x) / self.viewport_zoom
            screen_pos_z = (zone_top_left_wld[1] - viewport_top_left_z) / self.viewport_zoom
            screen_w = zone.dims[0] / self.viewport_zoom
            screen_h = zone.dims[1] / self.viewport_zoom
            zone_rect = pg.Rect(screen_pos_x, screen_pos_z, screen_w, screen_h)

            pg.draw.rect(self.surface, cols.MAP_PROHIBITED_BORDER_COLOR, zone_rect, 2)

            if show_advanced_info:
                text_centre = (screen_pos_x + screen_w / 2, screen_pos_z + screen_h / 2)
                draw_text(self.surface, text_centre, 'centre', 'centre', zone.code, cols.MAP_PROHIBITED_TEXT_COLOUR, 20, self.game.assets.fonts.monospaced)


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
            self.surface.blit(rotated_runway_surface, runway_rect_on_map)

            runway_cx, runway_cy = runway_map_center_x, runway_map_center_y  # local alias

            # Show GPS pointer
            if runway is self.game.env.runways[self.plane.gps_runway_index]:
                gps_rect = self.game.assets.images.gps_dest_marker.get_rect(center=(runway_cx, runway_cy))
                self.surface.blit(self.game.assets.images.gps_dest_marker, gps_rect)

            # Runway information
            draw_text(self.surface, (runway_cx, runway_cy - 50), 'centre', 'centre', runway.name, cols.WHITE, 20, self.game.assets.fonts.monospaced)

            info_text = f"{runway.heading:03d}°, {units.convert_units(runway.pos.y, units.METRES, units.FEET):,.0f} ft"
            draw_text(self.surface, (runway_cx, runway_cy - 30), 'centre', 'centre', info_text, cols.WHITE, 15, self.game.assets.fonts.monospaced)

        # Draw plane icon
        cx, cz = C.MAP_OVERLAY_SIZE/2, C.MAP_OVERLAY_SIZE/2
        icon_x = cx - (self.viewport_pos.x - self.plane.pos.x) / self.viewport_zoom
        icon_z = cz - (self.viewport_pos.z - self.plane.pos.z) / self.viewport_zoom

        plane_icon_rotated = pg.transform.rotate(self.game.assets.images.plane_icon, -yaw)
        rotated_icon_rect = plane_icon_rotated.get_rect(center=(icon_x, icon_z))
        self.surface.blit(plane_icon_rotated, rotated_icon_rect)

        # Define scale bar size here as the world length is also used in grid rendering
        MAX_SCALE_BAR_SIZE = 80  # pixels
        target_size = self.viewport_zoom * MAX_SCALE_BAR_SIZE

        scale_bar_length_world = max([l for l in C.SCALE_BAR_LENGTHS if l <= target_size], default=C.SCALE_BAR_LENGTHS[0])

        # Show grid
        if show_advanced_info:
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

            label_font = pg.font.Font(self.game.assets.fonts.monospaced, 18)

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
            self.surface.blit(self.grid_surface, (0, 0))

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
        pg.draw.polygon(self.surface, cols.WHITE, arrow_points)
        draw_text(self.surface, (ni_center_x, ni_center_y - north_indicator_offset_y), 'centre', 'top', "N", cols.WHITE, 25, self.game.assets.fonts.monospaced)

        # Draw scale bar
        scale_bar_offset = (12, 80)

        scale_bar_length_pix = scale_bar_length_world / self.viewport_zoom
        scale_bar_rect = pg.Rect(scale_bar_offset[0], scale_bar_offset[1], scale_bar_length_pix, 5)

        pg.draw.rect(self.surface, cols.WHITE, scale_bar_rect)
        draw_text(self.surface, (scale_bar_offset[0], scale_bar_offset[1] + 20), 'left', 'centre', f"{scale_bar_length_world:,} m", cols.WHITE, 20, self.game.assets.fonts.monospaced)

        # Calculate ground speed
        ground_speed_vec = pg.Vector3(self.plane.vel.x, 0, self.plane.vel.z)
        ground_speed_mag = ground_speed_vec.length()

        draw_text(self.surface, (C.MAP_OVERLAY_SIZE//2 - 100, 30), 'left', 'centre', 'GS', (100, 255, 255), 25, self.game.assets.fonts.monospaced)
        draw_text(self.surface, (C.MAP_OVERLAY_SIZE//2 - 45, 30), 'left', 'centre', f"{units.convert_units(ground_speed_mag, units.METRES/units.SECONDS, units.KNOTS):,.0f}", cols.WHITE, 25, self.game.assets.fonts.monospaced)

        # Calculate ETA
        dest_runway = self.game.env.runways[self.plane.gps_runway_index]

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

        draw_text(self.surface, (C.MAP_OVERLAY_SIZE//2 - 100, 55), 'left', 'centre', 'ETA', (100, 255, 255), 25, self.game.assets.fonts.monospaced)
        draw_text(self.surface, (C.MAP_OVERLAY_SIZE//2 - 45, 55), 'left', 'centre', eta_text, cols.WHITE, 25, self.game.assets.fonts.monospaced)

        # Blit the completed map to the main HUD surface
        map_rect = self.surface.get_rect(center=(map_centre))
        surface.blit(self.surface, map_rect)

        # Show height key
        if show_advanced_info:
            surface.blit(
                self.height_legend_surface,
                (C.WN_W//2 - C.MAP_OVERLAY_SIZE//2 - 200, map_centre[1] - 180)
            )
