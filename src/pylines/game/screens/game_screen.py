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
from math import sin, cos, radians as rad
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Callable, cast

import numpy as np
import pygame as pg
from OpenGL import GL as gl

import pylines.core.colours as cols
import pylines.core.constants as C
import pylines.core.paths as paths
import pylines.core.units as units
from pylines.core.custom_types import Colour, EventList, RealNumber
from pylines.core.time_manager import (
    brightness_from_hour,
    fetch_hour,
    sky_colour_from_hour,
)
from pylines.core.utils import clamp, draw_needle, draw_text, draw_transparent_rect
from pylines.game.states import State
from pylines.objects.buildings import (
    BuildingDefinition,
    BuildingMapIconType,
    draw_building_icon,
)
from pylines.objects.objects import CrashReason, Plane
from pylines.objects.scenery.ground import Ground
from pylines.objects.scenery.ocean import Ocean
from pylines.objects.scenery.runway import Runway
from pylines.objects.scenery.sky import Moon, Sky, Sun
from pylines.shaders.shader_manager import load_shader_script

if TYPE_CHECKING:
    from pylines.core.custom_types import ScancodeWrapper, Surface
    from pylines.game.game import Game

class MapState(Enum):
    HIDDEN = 0
    SHOWN = 1

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
        assets = game.assets
        super().__init__(game)

        self._frame_count = 0
        self.env = self.game.env
        self.dialog_box = DialogMessage()

        ground_textures = {
            "sand_texture": assets.images.sand,
            "low_grass_texture": assets.images.low_grass,
            "high_grass_texture": assets.images.high_grass,
            "treeline_rock_texture": assets.images.treeline_rock,
            "alpine_rock_texture": assets.images.alpine_rock,
            "snow_texture": assets.images.snow,
            "noise": assets.world.noise,
        }
        self.ocean = Ocean(assets.images.ocean, game.env)
        self.ground = Ground(ground_textures, game.env)

        self.plane = Plane(assets.sounds, self.dialog_box, game.env)
        self.sky = Sky()
        self.sun = Sun(assets.images.sun)
        self.moon = Moon(assets.images.moon)
        self.show_stall_warning: bool = False
        self.show_overspeed_warning: bool = False
        self.time_elapsed: int = 0  # milliseconds

        self.channel_engine_ambient = pg.mixer.Channel(C.SFXChannelID.ENGINE_AMBIENT)
        self.channel_engine_active = pg.mixer.Channel(C.SFXChannelID.ENGINE_ACTIVE)
        self.channel_wind = pg.mixer.Channel(C.SFXChannelID.WIND)

        self.channel_stall = pg.mixer.Channel(C.SFXChannelID.STALL)
        self.channel_overspeed = pg.mixer.Channel(C.SFXChannelID.OVERSPEED)
        self.channel_prohibited = pg.mixer.Channel(C.SFXChannelID.PROHIBITED)

        # Font for text rendering
        self.font = pg.font.Font(assets.fonts.monospaced, 36)

        # GPS destination
        self.gps_runway_index: int = 1

        # Graphics
        self.hud_tex = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.hud_tex)

        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

        # Allocate empty texture
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_RGBA,
            C.WN_W,
            C.WN_H,
            0,
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            None
        )

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        self.hud_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)

        ai_size = 170, 170
        inner_ai_rect = pg.Rect(0, 0, ai_size[0]-4, ai_size[1]-4)
        self.ai_mask = pg.Surface(inner_ai_rect.size, pg.SRCALPHA)
        pg.draw.circle(
            self.ai_mask,
            (255, 255, 255),
            (inner_ai_rect.width//2, inner_ai_rect.height//2),
            inner_ai_rect.width//2
        )

        # Map setup
        self.map_up: RealNumber = 0  # 1 = fully up, 0 = fully down
        self.map_state: MapState = MapState.HIDDEN
        self.map_show_advanced_info = False

        def height_to_colour(h: float) -> Colour:
            lerp_colour: Callable = cols.lerp_colour

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

        # Make cache directory
        cache_dir = paths.CACHE_DIR / "map_tiles"
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
                current_tile = pg.Surface((C.MAP_PIXELS_PER_TILE, C.MAP_PIXELS_PER_TILE))
                pix_array = pg.PixelArray(current_tile)

                # Loop over pixels within a tile
                for pix_z in range(C.MAP_PIXELS_PER_TILE):
                    for pix_x in range(C.MAP_PIXELS_PER_TILE):
                        world_x = tile_start_x + pix_x * C.MAP_METRES_PER_PX
                        world_z = tile_start_z + pix_z * C.MAP_METRES_PER_PX
                        pix_array[pix_x, pix_z] = HEIGHT_COLOUR_LOOKUP[clamp(  # type: ignore[index]
                            int(self.game.env.height_at(world_x, world_z)), (-4_000, 6_000)
                        ) + 4_000]

                del pix_array  # Unlock the Surface so it can be used
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

        # Building rendering setup
        all_vertices = []
        for building in self.env.buildings:
            all_vertices.extend(building.get_vertices())

        if all_vertices:
            self.building_vertices = np.array(all_vertices, dtype=np.float32)
            self.building_vertex_count = len(self.building_vertices) // 10

            self.buildings_vbo = gl.glGenBuffers(1)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buildings_vbo)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, self.building_vertices.nbytes, self.building_vertices, gl.GL_STATIC_DRAW)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

            self.building_shader = load_shader_script(
                str(paths.SHADERS_DIR / "building.vert"),
                str(paths.SHADERS_DIR / "building.frag")
            )
            self.building_pos_loc = gl.glGetAttribLocation(self.building_shader, "position")
            self.building_color_loc = gl.glGetAttribLocation(self.building_shader, "color")
            self.building_normal_loc = gl.glGetAttribLocation(self.building_shader, "normal")
            self.building_emissive_loc = gl.glGetAttribLocation(self.building_shader, "in_emissive")
            self.building_brightness_loc = gl.glGetUniformLocation(self.building_shader, "u_brightness")
        else:
            self.building_vertices = np.array([], dtype=np.float32)
            self.building_vertex_count = 0
            self.buildings_vbo = None

    def reset(self) -> None:
        self.plane.reset()

        self.channel_wind.stop()
        self.channel_engine_active.stop()
        self.channel_engine_ambient.stop()

        self.channel_stall.stop()
        self.channel_overspeed.stop()

        self.sounds.menu_music.fadeout(1_500)
        self.dialog_box.reset()
        self.time_elapsed = 0

    def update(self, dt: int):
        self._frame_count += 1
        self.time_elapsed += dt
        self.dialog_box.update(dt)

        self.sun.update()
        self.moon.update()

        if self.plane.crashed:
            self.dialog_box.reset()
            self.channel_stall.stop()
            self.channel_overspeed.stop()

            self.channel_wind.stop()
            self.channel_engine_active.stop()
            self.channel_engine_ambient.stop()

            return

        # Map update
        if self.map_state == MapState.HIDDEN:
            self.map_up -= (dt/1000) / C.MAP_TOGGLE_ANIMATION_DURATION
        else:
            self.map_up += (dt/1000) / C.MAP_TOGGLE_ANIMATION_DURATION
        self.map_up = clamp(self.map_up, (0, 1))

        self.plane.update(dt)

        # Stall warning
        self.show_stall_warning = self.plane.stalled
        if self.show_stall_warning:
            if not self.channel_stall.get_busy():
                self.channel_stall.play(self.sounds.stall_warning, loops=-1)
        else:
            self.channel_stall.stop()

        # Overspeed warning
        self.show_overspeed_warning = self.plane.vel.length() > self.plane.model.v_ne  # Both in m/s
        if self.show_overspeed_warning:
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

        # Prohibited zone warning
        def plane_in_prohibited_zone() -> bool:
            for zone in self.env.prohibited_zones:
                px, _, pz = self.plane.pos
                zone_centre_x, zone_centre_z = zone.pos
                zone_w, zone_h = zone.dims

                zone_min_x = zone_centre_x - zone_w / 2
                zone_max_x = zone_centre_x + zone_w / 2
                zone_min_z = zone_centre_z - zone_h / 2
                zone_max_z = zone_centre_z + zone_h / 2

                if zone_min_x < px < zone_max_x and zone_min_z < pz < zone_max_z:
                    return True

            return False

        self.show_prohibited_zone_warning = plane_in_prohibited_zone()
        if self.show_prohibited_zone_warning:
            if not self.channel_prohibited.get_busy():
                self.channel_prohibited.play(self.sounds.prohibited_zone_warning, loops=-1)
            self.dialog_box.set_message("Immediately exit this zone - penalties may apply", (255, 127, 0), 100)
        else:
            self.channel_prohibited.stop()

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        # Meta controls
        if self.pressed(keys, pg.K_p):
            self.sounds.menu_music.stop()
            self.game.enter_state(self.game.States.TITLE)

            self.channel_wind.stop()
            self.channel_engine_active.stop()
            self.channel_engine_ambient.stop()

        if self.pressed(keys, pg.K_r):  # r to reset
            self.plane.reset()
            self.gps_runway_index = 1  # reset gps waypoint

        # Block flight controls if crashed or disabled
        if not self.plane.flyable:
            self.update_prev_keys(keys)
            return

        # Show/hide map
        if self.pressed(keys, pg.K_m):
            self.map_state = MapState.HIDDEN if self.map_state == MapState.SHOWN else MapState.SHOWN

        # Cycle GPS waypoint
        if self.pressed(keys, pg.K_g):
            self.gps_runway_index = (self.gps_runway_index + 1) % len(self.env.runways)

        if self.map_state == MapState.SHOWN:
            # While map is shown: control zoom
            if keys[pg.K_w]:
                self.viewport_zoom /= 2.5 ** (dt/1000)
            if keys[pg.K_s]:
                self.viewport_zoom *= 2.5 ** (dt/1000)
            self.viewport_zoom = clamp(self.viewport_zoom, (1, 100))
        else:
            # Throttle controls
            throttle_speed = 0.4 * dt/1000
            if keys[pg.K_w]:
                self.plane.throttle_frac += throttle_speed
            if keys[pg.K_s]:
                self.plane.throttle_frac -= throttle_speed
            self.plane.throttle_frac = clamp(self.plane.throttle_frac, (0, 1))

        self.map_show_advanced_info = self.map_state == MapState.SHOWN and keys[pg.K_h]

        # Turning authority
        base_rot_accel = 20 * dt/1000
        control_authority = 1 - 0.875 * self.plane.damage_level**2  # reduce authority based on damage level
        speed_authority_factor = clamp((self.plane.vel.length()/30.87)**2, (0.01, 1))  # based on vel in m/s
        rot_accel = control_authority * base_rot_accel * speed_authority_factor * (0.2 if self.plane.on_ground else 1)

        # Turning or map panning
        if self.map_state == MapState.SHOWN:
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
            if keys[pg.K_UP]:
                self.plane.rot_rate.x += rot_accel * (1 - (self.plane.rot.x / 90))
            if keys[pg.K_DOWN]:
                self.plane.rot_rate.x -= rot_accel * (1 + (self.plane.rot.x / 90))

            # Turning
            if keys[pg.K_LEFT]:
                self.plane.rot_rate.z -= rot_accel
            if keys[pg.K_RIGHT]:
                self.plane.rot_rate.z += rot_accel

        # Input stabilisation
        if (not (keys[pg.K_UP] or keys[pg.K_DOWN])) or self.map_state == MapState.HIDDEN:
            self.plane.rot_rate.x *= (1 - 0.8 * dt/1000)
        if (not (keys[pg.K_LEFT] or keys[pg.K_RIGHT])) or self.map_state == MapState.HIDDEN:
            self.plane.rot_rate.z *= (1 - 0.8 * dt/1000)

        # Flaps
        FLAPS_SPEED = 2
        if keys[pg.K_z]:  # Flaps up
            self.plane.flaps += FLAPS_SPEED * dt/1000
        if keys[pg.K_x]:  # Flaps down
            self.plane.flaps -= FLAPS_SPEED * dt/1000
        self.plane.flaps = clamp(self.plane.flaps, (0, 1))

        # Rudder
        RUDDER_SPEED = 2.5
        RUDDER_SNAPBACK = 3
        if keys[pg.K_a]:
            self.plane.rudder -= RUDDER_SPEED * dt/1000
        if keys[pg.K_d]:
            self.plane.rudder += RUDDER_SPEED * dt/1000
        if not (keys[pg.K_a] or keys[pg.K_d]):
            decay = RUDDER_SNAPBACK * dt/1000
            self.plane.rudder *= max(0, 1 - decay)
        self.plane.rudder = clamp(self.plane.rudder, (-1, 1))

        # Brakes
        self.plane.braking = keys[pg.K_b]  # b to brake

        self.update_prev_keys(keys)

    def draw_buildings(self):
        if not self.building_vertex_count or self.buildings_vbo is None:
            return

        gl.glUseProgram(self.building_shader)

        # Set uniforms
        brightness = brightness_from_hour(fetch_hour())
        gl.glUniform1f(self.building_brightness_loc, brightness)

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

    def draw_map(self):
        hud_surface = self.hud_surface
        NUM_TILES = math.ceil(C.HALF_WORLD_SIZE*2 / (C.METRES_PER_TILE))
        MAP_OVERLAY_SIZE = 500  # size of the map overlay in pixels
        MAP_BORDER_COLOUR = (129, 137, 143)

        if self.viewport_auto_panning:
            self.viewport_pos = self.plane.pos.copy()

        px, _, pz = self.viewport_pos

        # Render base map
        map_centre = C.WN_W//2, int(285 + C.WN_H * (1-self.map_up))

        # Map border
        outer_map_rect = pg.Rect(0, 0, MAP_OVERLAY_SIZE+10, MAP_OVERLAY_SIZE+10)
        outer_map_rect.center = map_centre
        pg.draw.rect(hud_surface, MAP_BORDER_COLOUR, outer_map_rect)

        # Base
        map_surface = pg.Surface((MAP_OVERLAY_SIZE, MAP_OVERLAY_SIZE))
        map_surface.fill((0, 0, 0))

        # Draw map tiles
        # World coordinates of the top-left corner of the map viewport
        viewport_half_size_metres = MAP_OVERLAY_SIZE / 2 * self.viewport_zoom
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

                # Position of the tile on the screen
                screen_pos_x = (tile_world_x - viewport_top_left_x) / self.viewport_zoom
                screen_pos_z = (tile_world_z - viewport_top_left_z) / self.viewport_zoom

                tile_size_on_screen = C.METRES_PER_TILE / self.viewport_zoom

                dest_rect = pg.Rect(
                    screen_pos_x,
                    screen_pos_z,
                    tile_size_on_screen,
                    tile_size_on_screen,
                )

                scaled_tile = pg.transform.scale(tile_surface, (int(tile_size_on_screen) + 1, int(tile_size_on_screen) + 1))
                map_surface.blit(scaled_tile, dest_rect)

        # Show buildings
        if self.viewport_zoom < 10:  # Only show if zoomed in far enough for performance
            for building in self.env.buildings:
                # Calculate screen position for the building
                screen_x = (building.pos.x - viewport_top_left_x) / self.viewport_zoom
                screen_y = (building.pos.z - viewport_top_left_z) / self.viewport_zoom

                SAFETY_BUFFER = 25  # for smoothness
                if (-SAFETY_BUFFER < screen_x < MAP_OVERLAY_SIZE + SAFETY_BUFFER
                and -SAFETY_BUFFER < screen_y < MAP_OVERLAY_SIZE + SAFETY_BUFFER):
                    # Retrieve building definition
                    def_ = self.env.building_defs[building.type_]

                    # Draw the building icon
                    draw_building_icon(map_surface, screen_x, screen_y, def_.appearance, self.viewport_zoom)

        # Show buliding legend if advanced map info is enabled
        if self.map_show_advanced_info:
            draw_transparent_rect(
                hud_surface,
                (map_centre[0] + MAP_OVERLAY_SIZE/2 + 20, map_centre[1] - 180),
                (200, 360), border_thickness=2, border_colour=MAP_BORDER_COLOUR
            )

            draw_text(hud_surface, (map_centre[0] + MAP_OVERLAY_SIZE/2 + 120, map_centre[1] - 155), 'centre', 'centre', "Buildings", (255, 255, 255), 20, self.fonts.monospaced)

            screen_y = map_centre[1] - 120
            items = list(self.env.building_defs.items())

            def icon_height(info: BuildingDefinition):
                icon = info.appearance.icon
                dims = info.appearance.dims
                if icon == BuildingMapIconType.POINT:
                    return 0
                if icon == BuildingMapIconType.CIRCLE:
                    return cast(tuple[int], dims)[0] * 2   # radius → diameter
                if icon == BuildingMapIconType.SQUARE:
                    return cast(tuple[int, int], dims)[1]

                return 0  # fallback

            for idx, (name, def_) in enumerate(items):
                # draw icon + label
                draw_text(
                    hud_surface,
                    (map_centre[0] + MAP_OVERLAY_SIZE/2 + 90, screen_y),
                    'left', 'centre',
                    f"{name}",
                    (255, 255, 255), 15,
                    self.fonts.monospaced
                )
                draw_building_icon(
                    hud_surface,
                    map_centre[0] + MAP_OVERLAY_SIZE/2 + 55,
                    screen_y,
                    def_.appearance
                )

                # Compute spacing for next line
                curr_h = icon_height(def_)
                next_h = icon_height(items[idx + 1][1]) if idx + 1 < len(items) else 0

                # Apply line spacing
                line_h = max(15, 15 + curr_h//2 + next_h//2)
                screen_y += line_h

        # Draw prohibited zones
        for zone in self.env.prohibited_zones:
            ZONE_FILL_COLOR = (255, 0, 0, 51)
            ZONE_BORDER_COLOR = (255, 0, 0, 255)

            # Calculate top-left corner in world coordinates
            zone_top_left_wld = zone.pos[0] - zone.dims[0] / 2, zone.pos[1] - zone.dims[1] / 2

            # Calculate screen position and dimensions
            screen_pos_x = (zone_top_left_wld[0] - viewport_top_left_x) / self.viewport_zoom
            screen_pos_z = (zone_top_left_wld[1] - viewport_top_left_z) / self.viewport_zoom
            screen_w = zone.dims[0] / self.viewport_zoom
            screen_h = zone.dims[1] / self.viewport_zoom

            zone_rect = pg.Rect(screen_pos_x, screen_pos_z, screen_w, screen_h)

            # Draw filled rectangle (20% opacity)
            # Create a semi-transparent surface for the fill
            zone_fill_surface = pg.Surface(zone_rect.size, pg.SRCALPHA)
            zone_fill_surface.fill(ZONE_FILL_COLOR)
            map_surface.blit(zone_fill_surface, zone_rect.topleft)

            # Draw border (solid red, 2 pixels wide)
            pg.draw.rect(map_surface, ZONE_BORDER_COLOR, zone_rect, 2)

            ZONE_TEXT_COLOUR = (255, 210, 210)
            if self.map_show_advanced_info:
                text_centre = (screen_pos_x + screen_w / 2, screen_pos_z + screen_h / 2)
                draw_text(map_surface, text_centre, 'centre', 'centre', zone.code, ZONE_TEXT_COLOUR, 20, self.fonts.monospaced)

        # Draw runways
        for runway in self.env.runways:
            # Convert runway world dimensions to map pixel dimensions, 1 pix min size
            runway_width_on_map = max(1, int(runway.w / self.viewport_zoom))
            runway_length_on_map = max(1, int(runway.l / self.viewport_zoom))

            # Create a base surface for the runway. Its length (l) will align with the Y-axis when unrotated.
            runway_surface_base = pg.Surface((runway_width_on_map, runway_length_on_map), pg.SRCALPHA)
            runway_surface_base.fill((175, 175, 175))

            rotated_runway_surface = pg.transform.rotate(runway_surface_base, -runway.heading)

            # Calculate the runway's center position on the map_surface in pixels.
            runway_map_center_x = (runway.pos.x - viewport_top_left_x) / self.viewport_zoom
            runway_map_center_y = (runway.pos.z - viewport_top_left_z) / self.viewport_zoom

            # Get bounding rectangle for the rotated surface and set its center.
            runway_rect_on_map = rotated_runway_surface.get_rect(center=(runway_map_center_x, runway_map_center_y))

            # Blit runway onto map surface
            map_surface.blit(rotated_runway_surface, runway_rect_on_map)

            runway_cx, runway_cy = runway_map_center_x, runway_map_center_y  # local alias

            # Show GPS pointer
            if runway is self.env.runways[self.gps_runway_index]:
                gps_rect = self.images.gps_dest_marker.get_rect(center=(runway_cx, runway_cy))
                map_surface.blit(self.images.gps_dest_marker, gps_rect)

            # Runway information
            draw_text(map_surface, (runway_cx, runway_cy - 50), 'centre', 'centre', runway.name, (255, 255, 255), 20, self.fonts.monospaced)

            info_text = f"{runway.heading:03d}°, {units.convert_units(runway.pos.y, units.METRES, units.FEET):,.0f} ft"
            draw_text(map_surface, (runway_cx, runway_cy - 30), 'centre', 'centre', info_text, (255, 255, 255), 15, self.fonts.monospaced)

        # Draw plane icon
        cx, cz = MAP_OVERLAY_SIZE/2, MAP_OVERLAY_SIZE/2
        icon_x = cx - (self.viewport_pos.x - self.plane.pos.x) / self.viewport_zoom
        icon_z = cz - (self.viewport_pos.z - self.plane.pos.z) / self.viewport_zoom

        icon_rect = self.images.plane_icon.get_rect(center=(icon_x, icon_z))
        plane_icon_rotated = pg.transform.rotate(self.images.plane_icon, -self.plane.rot.y)
        map_surface.blit(plane_icon_rotated, icon_rect)

        # Define scale bar size here as the world length is also used in grid rendering
        SCALE_BAR_LENGTHS = [25, 100, 500, 1_000, 2_000, 5_000, 10_000]
        MAX_SCALE_BAR_SIZE = 80  # pixels
        target_size = self.viewport_zoom * MAX_SCALE_BAR_SIZE

        scale_bar_length_world = max([l for l in SCALE_BAR_LENGTHS if l <= target_size], default=SCALE_BAR_LENGTHS[0])

        # Show grid
        if self.map_show_advanced_info:
            GRID_MINOR_COL = (255, 255, 255, 80)
            GRID_MAJOR_COL = (255, 255, 255, 140)
            GREEN = (0, 255, 0)

            MINOR_INTERVAL = scale_bar_length_world
            MAJOR_INTERVAL = 5 * MINOR_INTERVAL

            # Draw grid
            grid_surface = pg.Surface((MAP_OVERLAY_SIZE, MAP_OVERLAY_SIZE), pg.SRCALPHA)

            def world_to_map(world_x, world_z) -> tuple[float, float]:
                screen_x = (world_x - viewport_top_left_x) * (1/self.viewport_zoom)
                screen_y = (world_z - viewport_top_left_z) * (1/self.viewport_zoom)
                return screen_x, screen_y

            # Grid overlay bounds
            start_grid_x = int(viewport_top_left_x // MINOR_INTERVAL) * MINOR_INTERVAL
            end_grid_x = int((viewport_top_left_x + MAP_OVERLAY_SIZE * self.viewport_zoom) // MINOR_INTERVAL) * MINOR_INTERVAL + MINOR_INTERVAL
            start_grid_z = int(viewport_top_left_z // MINOR_INTERVAL) * MINOR_INTERVAL
            end_grid_z = int((viewport_top_left_z + MAP_OVERLAY_SIZE * self.viewport_zoom) // MINOR_INTERVAL) * MINOR_INTERVAL + MINOR_INTERVAL

            # Draw grid
            for world_x in range(start_grid_x, end_grid_x, MINOR_INTERVAL):
                p1 = world_to_map(world_x, viewport_top_left_z)
                p2 = world_to_map(world_x, viewport_top_left_z + MAP_OVERLAY_SIZE * self.viewport_zoom)
                pg.draw.line(grid_surface, GRID_MAJOR_COL if abs(world_x % MAJOR_INTERVAL) < C.EPSILON else GRID_MINOR_COL, p1, p2, 1)

                if abs(world_x % MAJOR_INTERVAL) <= C.EPSILON:
                    draw_text(grid_surface, (p1[0], MAP_OVERLAY_SIZE - 15), 'centre', 'centre', f"{int(world_x):,.0f}", (255, 255, 255), 18, self.fonts.monospaced)

            for world_z in range(start_grid_z, end_grid_z, MINOR_INTERVAL):
                p1 = world_to_map(viewport_top_left_x, world_z)
                p2 = world_to_map(viewport_top_left_x + MAP_OVERLAY_SIZE * self.viewport_zoom, world_z)
                pg.draw.line(grid_surface, GRID_MAJOR_COL if abs(world_z % MAJOR_INTERVAL) < C.EPSILON else GRID_MINOR_COL, p1, p2, 1)

                if abs(world_z % MAJOR_INTERVAL) <= C.EPSILON:
                    draw_text(grid_surface, (5, p1[1]), 'left', 'centre', f"{int(world_z):,.0f}", (255, 255, 255), 18, self.fonts.monospaced)

            # Draw origin
            origin_map_x, origin_map_y = world_to_map(0, 0)
            if 0 <= origin_map_x <= MAP_OVERLAY_SIZE and 0 <= origin_map_y <= MAP_OVERLAY_SIZE:
                pg.draw.circle(grid_surface, GREEN, (origin_map_x, origin_map_y), 5)

            # Blit grid surface onto map surface
            map_surface.blit(grid_surface, (0, 0))

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
        pg.draw.polygon(map_surface, cols.WHITE, arrow_points)
        draw_text(map_surface, (ni_center_x, ni_center_y - north_indicator_offset_y), 'centre', 'top', "N", cols.WHITE, 25, self.fonts.monospaced)

        # Draw scale bar
        scale_bar_offset = (12, 80)

        scale_bar_length_pix = scale_bar_length_world / self.viewport_zoom
        scale_bar_rect = pg.Rect(scale_bar_offset[0], scale_bar_offset[1], scale_bar_length_pix, 5)

        pg.draw.rect(map_surface, (255, 255, 255), scale_bar_rect)
        draw_text(map_surface, (scale_bar_offset[0], scale_bar_offset[1] + 20), 'left', 'centre', f"{scale_bar_length_world:,} m", cols.WHITE, 20, self.fonts.monospaced)

        # Calculate ground speed
        ground_speed_vec = pg.Vector3(self.plane.vel.x, 0, self.plane.vel.z)
        ground_speed_mag = ground_speed_vec.length()

        draw_text(map_surface, (MAP_OVERLAY_SIZE//2 - 100, 30), 'left', 'centre', 'GS', (100, 255, 255), 25, self.fonts.monospaced)
        draw_text(map_surface, (MAP_OVERLAY_SIZE//2 - 45, 30), 'left', 'centre', f"{units.convert_units(ground_speed_mag, units.METRES/units.SECONDS, units.KNOTS):,.0f}", (255, 255, 255), 25, self.fonts.monospaced)

        # Calculate ETA
        dest_runway = self.env.runways[self.gps_runway_index]

        # Take out vertical components of relevant vectors
        dest_pos_flat = pg.Vector3(dest_runway.pos.x, 0, dest_runway.pos.z)
        plane_pos_flat = pg.Vector3(self.plane.pos.x, 0, self.plane.pos.z)
        vel_flat = pg.Vector3(self.plane.vel.x, 0, self.plane.vel.z)

        vec_to_dest = dest_pos_flat - plane_pos_flat
        distance = vec_to_dest.length()

        if distance <= C.EPSILON:
            # Very small distance -> already at destination
            eta_seconds = 0
        else:
            direction = vec_to_dest.normalize()
            ground_speed_towards_dest = vel_flat.dot(direction)

            eta_seconds: float | None
            if ground_speed_towards_dest <= C.EPSILON:
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

        draw_text(map_surface, (MAP_OVERLAY_SIZE//2 - 100, 55), 'left', 'centre', 'ETA', (100, 255, 255), 25, self.fonts.monospaced)
        draw_text(map_surface, (MAP_OVERLAY_SIZE//2 - 45, 55), 'left', 'centre', eta_text, (255, 255, 255), 25, self.fonts.monospaced)

        # Blit the completed map to the main HUD surface
        map_rect = map_surface.get_rect(center=(map_centre))
        hud_surface.blit(map_surface, map_rect)

        # Show height key
        if self.map_show_advanced_info:
            draw_transparent_rect(
                hud_surface,
                (C.WN_W//2 - MAP_OVERLAY_SIZE//2 - 200, map_centre[1] - 180),
                (180, 360), border_thickness=2, border_colour=MAP_BORDER_COLOUR
            )

            hud_surface.blit(self.height_key, (C.WN_W//2 - MAP_OVERLAY_SIZE//2 - 95, map_centre[1] - 125))
            draw_text(hud_surface, (C.WN_W//2 - MAP_OVERLAY_SIZE//2 - 110, map_centre[1] - 155), 'centre', 'centre', "Altitude (ft)", (255, 255, 255), 20, self.fonts.monospaced)

            # Show heightmap labels in feet
            for h in range(-12_000, 18_001, 2_000):
                text_y = map_centre[1] - 125 + (self.HEIGHT_KEY_H * (1 - ((h + 12_000) / 30_000)))
                draw_text(hud_surface, (C.WN_W//2 - MAP_OVERLAY_SIZE//2 - 100, text_y), 'right', 'centre', f"{h:,.0f}", (255, 255, 255), 15, self.fonts.monospaced)

    def draw_hud(self):
        pitch, yaw, roll = self.plane.rot
        hud_surface = self.hud_surface
        hud_surface.fill((0, 0, 0, 0))  # clear with transparency

        # Exit controls
        if self.time_elapsed < 5_000 or not self.plane.flyable:
            draw_text(hud_surface, (15, 30), 'left', 'centre', "R    restart flight", (255, 255, 255), 30, self.fonts.monospaced)
            draw_text(hud_surface, (15, 60), 'left', 'centre', "P    quit to menu", (255, 255, 255), 30, self.fonts.monospaced)

        # Stall warning
        warning_x = C.WN_W//2-145
        if self.show_stall_warning:
            draw_text(hud_surface, (C.WN_W//2, C.WN_H*0.62), 'centre', 'centre', "STALL", (210, 0, 0), 50, self.fonts.monospaced)

        # Overspeed warning
        warning_x = C.WN_W//2+145
        if self.show_overspeed_warning:
            draw_text(hud_surface, (C.WN_W//2, C.WN_H*0.57), 'centre', 'centre', "OVERSPEED", (210, 0, 0), 50, self.fonts.monospaced)

        # Damage overlay
        if self.plane.damage_level > 0:
            overlays = self.images.damage_overlays
            # Damage_level is 0-1, so we can map it to the number of overlays
            overlay_idx = min(len(overlays) - 1, int(self.plane.damage_level * (len(overlays))))
            overlay = overlays[overlay_idx]
            hud_surface.blit(overlay, (0, 0))

        # Draw cockpit
        cockpit = self.images.cockpit
        cockpit_w, cockpit_h = cockpit.get_size()
        x = (C.WN_W - cockpit_w) // 2   # centre horizontally (optional)
        y = C.WN_H - cockpit_h          # bottom-aligned
        hud_surface.blit(cockpit, (x, y))

        # Compass (heading + ground track)
        centre = (C.WN_W//2-300, C.WN_H*0.85)
        compass_rot = pg.transform.rotate(self.images.compass, yaw)
        rect = compass_rot.get_rect(center=centre)
        hud_surface.blit(compass_rot, rect)

        vel_flat = pg.Vector3(self.plane.vel.x, 0, self.plane.vel.z)
        ground_track_deg = math.degrees(
            math.atan2(vel_flat.x, -vel_flat.z)
        ) % 360 if vel_flat.length() >= C.EPSILON else 0

        selected_runway: Runway = self.env.runways[self.gps_runway_index]
        gps_distance = selected_runway.pos - self.plane.pos
        gps_distance_flat = pg.Vector3(gps_distance.x, 0, gps_distance.z)
        gps_bearing = math.degrees(
            math.atan2(gps_distance_flat.x, -gps_distance_flat.z)
        ) % 360 if gps_distance_flat.length() >= C.EPSILON else 0

        # Ground track (the actual velocity vector of the plane)
        draw_needle(hud_surface, centre, 90 - (ground_track_deg-yaw), 100, (255, 190, 0))
        # Heading (where the nose points)
        draw_needle(hud_surface, centre, 90, 100, (255, 0, 0))
        # GPS distance (where the nose points)
        draw_needle(hud_surface, centre, 90 - (gps_bearing-yaw), 100, (0, 255, 0))

        # Show runway alignment (blue needle)
        if gps_distance_flat.length() < 8000:
            draw_needle(hud_surface, centre, 90 - (selected_runway.heading-yaw), 50, (0, 120, 255))
            draw_needle(hud_surface, centre, 270 - (selected_runway.heading-yaw), 50, (0, 120, 255))

        # ASI (Airspeed Indicator)
        centre = (C.WN_W//2+300, C.WN_H*0.85)
        rect = self.images.speed_dial.get_rect(center=centre)
        hud_surface.blit(self.images.speed_dial, rect)

        speed_knots = self.plane.vel.length() * 1.94384  # Convert to knots
        angle = 90 - min(336, 270 * speed_knots/160)
        draw_text(hud_surface, (C.WN_W//2+300, C.WN_H*0.85 + 30), 'centre', 'centre', f"{int(self.plane.vel.length() * 1.94384):03d}", (192, 192, 192), 25, self.font)
        draw_needle(hud_surface, centre, angle, 100)

        # Altimeter (left)
        alt_centre = (C.WN_W//2 - 110, int(C.WN_H*0.74))
        alt_size = 160, 70
        alt_rect = pg.Rect(0, 0, *alt_size)
        alt_rect.center = alt_centre
        pg.draw.rect(hud_surface, (255, 255, 255), alt_rect)
        inner_alt_rect = pg.Rect(0, 0, alt_size[0]-4, alt_size[1]-4)
        inner_alt_rect.center = alt_centre
        pg.draw.rect(hud_surface, cols.BLACK, inner_alt_rect)
        draw_text(
            hud_surface,
            (alt_centre[0], alt_centre[1]-15),
            'centre', 'centre',
            f"{self.plane.pos.y * 3.28084:,.0f} ft",
            (255, 255, 255),
            27,
            self.fonts.monospaced
        )

        # VSI (below altimeter)
        vsi_centre = (alt_centre[0], alt_centre[1]+15)
        vs_ft_per_min = self.plane.vel.y * 196.85
        text_colour: Colour = cols.BLUE if vs_ft_per_min > 0 else cols.WHITE if vs_ft_per_min == 0 else cols.BROWN
        draw_text(
            hud_surface,
            vsi_centre,
            'centre', 'centre',
            f"{vs_ft_per_min:+,.0f}/min",
            text_colour,
            22,
            self.fonts.monospaced
        )

        # Location / LOC (right)
        loc_centre = (C.WN_W//2 + 85, int(C.WN_H*0.74))
        loc_size = 210, 70
        loc_rect = pg.Rect(0, 0, *loc_size)
        loc_rect.center = loc_centre
        pg.draw.rect(hud_surface, (255, 255, 255), loc_rect)
        inner_loc_rect = pg.Rect(0, 0, loc_size[0]-4, loc_size[1]-4)
        inner_loc_rect.center = loc_centre
        pg.draw.rect(hud_surface, cols.BLACK, inner_loc_rect)
        draw_text(
            hud_surface,
            loc_centre,
            'centre', 'centre',
            f"({self.plane.pos.x:,.0f}m, {self.plane.pos.z:,.0f}m)",
            (255, 255, 255),
            22,
            self.fonts.monospaced
        )

        # Time readout
        time_centre = (C.WN_W//2 - 130, int(C.WN_H*0.81))
        time_size = 100, 30
        time_rect = pg.Rect(0, 0, *time_size)
        time_rect.center = time_centre
        pg.draw.rect(hud_surface, (255, 255, 255), time_rect)
        inner_time_rect = pg.Rect(0, 0, time_size[0]-4, time_size[1]-4)
        inner_time_rect.center = time_centre
        pg.draw.rect(hud_surface, cols.BLACK, inner_time_rect)

        now = datetime.now().astimezone()
        offset_hours = int(cast(timedelta, now.utcoffset()).total_seconds() // 3600)
        draw_text(
            hud_surface,
            time_centre,
            'centre', 'centre',
            f"{now.hour:02d}:{now.minute:02d} ({offset_hours:+d})",
            (255, 255, 255),
            18,
            self.fonts.monospaced
        )

        # AGL readout
        agl_centre = (C.WN_W//2 + 130, int(C.WN_H*0.81))
        agl_size = 100, 30
        agl_rect = pg.Rect(0, 0, *agl_size)
        agl_rect.center = agl_centre
        pg.draw.rect(hud_surface, (255, 255, 255), agl_rect)
        inner_agl_rect = pg.Rect(0, 0, agl_size[0]-4, agl_size[1]-4)
        inner_agl_rect.center = agl_centre
        pg.draw.rect(hud_surface, cols.BLACK, inner_agl_rect)

        x, z = self.plane.pos.x, self.plane.pos.z
        altitude_agl = self.plane.pos.y - self.env.ground_height(x, z)
        draw_text(
            hud_surface,
            (agl_centre[0] - 45, agl_centre[1]),
            'left', 'centre',
            "AGL",
            (255, 255, 255),
            12,
            self.fonts.monospaced
        )
        draw_text(
            hud_surface,
            (agl_centre[0] + 45, agl_centre[1]),
            'right', 'centre',
            f"{units.convert_units(altitude_agl, units.METRES, units.FEET):,.0f} ft",
            (255, 255, 255),
            18,
            self.fonts.monospaced
        )

        # GPS information
        gps_centre = (C.WN_W//2 - 135, int(C.WN_H*0.87))
        gps_size = 80, 60
        gps_rect = pg.Rect(0, 0, *gps_size)
        gps_rect.center = gps_centre
        pg.draw.rect(hud_surface, (255, 255, 255), gps_rect)
        inner_gps_rect = pg.Rect(0, 0, gps_size[0]-4, gps_size[1]-4)
        inner_gps_rect.center = gps_centre
        pg.draw.rect(hud_surface, cols.BLACK, inner_gps_rect)

        draw_text(
            hud_surface,
            (gps_centre[0] - 35, gps_centre[1] - 14),
            'left', 'centre',
            selected_runway.name,
            (0, 120, 255),
            20,
            self.fonts.monospaced
        )

        draw_text(
            hud_surface,
            (gps_centre[0] - 35, gps_centre[1] + 14),
            'left', 'centre',
            f"{gps_distance_flat.length() / 1000:,.2f}km",
            (255, 255, 255),
            20,
            self.fonts.monospaced
        )

        # Glidescope
        glide_centre = (C.WN_W//2 + 105, int(C.WN_H*0.91))
        glide_size = 18, 125
        glide_rect = pg.Rect(0, 0, *glide_size)
        glide_rect.center = glide_centre
        pg.draw.rect(hud_surface, (255, 255, 255), glide_rect)
        inner_glide_rect = pg.Rect(0, 0, glide_size[0]-4, glide_size[1]-4)
        inner_glide_rect.center = glide_centre
        pg.draw.rect(hud_surface, cols.BLACK, inner_glide_rect)

        # Compute comparison for glidescope
        GLIDEPATH_SLOPE = math.tan(math.radians(3.0))  # glidescope is 3°
        expected_height_agl = gps_distance_flat.length() * GLIDEPATH_SLOPE
        expected_height_msl = expected_height_agl + selected_runway.pos.y
        deviation = self.plane.pos.y - expected_height_msl

        # Display glidescope
        show_glidescope = (
            gps_distance_flat.length() < 5_000 and  # runway is close
            self.plane.pos.y > self.env.ground_height(self.plane.pos.x, self.plane.pos.z)  # plane is still in the air
        )

        if show_glidescope:
            glide_centre_x, glide_centre_y = glide_centre

            # Tick marks
            pg.draw.line(hud_surface, (140, 140, 140), (glide_centre_x-7, glide_centre_y + 26), (glide_centre_x+6, glide_centre_y + 26), 2)
            pg.draw.line(hud_surface, (140, 140, 140), (glide_centre_x-7, glide_centre_y + 52), (glide_centre_x+6, glide_centre_y + 52), 2)
            pg.draw.line(hud_surface, (140, 140, 140), (glide_centre_x-7, glide_centre_y - 26), (glide_centre_x+6, glide_centre_y - 26), 2)
            pg.draw.line(hud_surface, (140, 140, 140), (glide_centre_x-7, glide_centre_y - 52), (glide_centre_x+6, glide_centre_y - 52), 2)

            # Green circle
            pg.draw.circle(hud_surface, (0, 255, 0), (glide_centre_x, glide_centre_y + clamp(deviation, (-10, 10)) * 52/10), 5)

            # White line
            pg.draw.line(hud_surface, (255, 255, 255), (glide_centre_x-7, glide_centre_y), (glide_centre_x+6, glide_centre_y), 2)

        # Throttle bar
        draw_text(hud_surface, (C.WN_W*0.86, C.WN_H*0.97), 'centre', 'centre', "Throttle", (25, 20, 18), 30, self.fonts.monospaced)
        pg.draw.line(hud_surface, (51, 43, 37), (C.WN_W*0.86, C.WN_H*0.94), (C.WN_W*0.86, C.WN_H*0.75), 3)
        size = 40, 20
        rect = pg.Rect(0, 0, *size)
        rect.center = (C.WN_W*0.86, C.WN_H*0.94 - C.WN_H*0.19*(self.plane.throttle_frac))  # type: ignore[arg-type]
        pg.draw.rect(hud_surface, (255, 255, 255), rect)

        # Flaps indicator
        pg.draw.line(hud_surface, (51, 43, 37), (C.WN_W*0.90, C.WN_H*0.93), (C.WN_W*0.90, C.WN_H*0.76), 3)
        size = 30, 15
        rect = pg.Rect(0, 0, *size)
        rect.center = (C.WN_W*0.90, C.WN_H*0.93 - C.WN_H*0.17*(self.plane.flaps))  # type: ignore[arg-type]
        pg.draw.rect(hud_surface, (220, 220, 220), rect)

        # Attitude indicator
        ai_centre = (C.WN_W//2, int(C.WN_H*0.89))
        ai_size = 170, 170
        ai_rect = pg.Rect(0, 0, *ai_size)
        ai_rect.center = ai_centre
        pg.draw.circle(hud_surface, (255, 255, 255), ai_centre, 85)
        inner_ai_rect = pg.Rect(0, 0, ai_size[0]-4, ai_size[1]-4)
        inner_ai_rect.center = ai_centre

        # AI fill surface (clipped)
        ai_surface = pg.Surface(inner_ai_rect.size, pg.SRCALPHA)

        tick_spacing = 5  # pixels per 5° of pitch

        # Horizon position (in local AI coords)
        horizon_y = inner_ai_rect.height // 2 - pitch * tick_spacing

        # Sky (above horizon)
        pg.draw.rect(
            ai_surface,
            cols.DARK_BLUE,
            (0, 0, inner_ai_rect.width, horizon_y)
        )

        # Ground (below horizon)
        pg.draw.rect(
            ai_surface,
            cols.DARK_BROWN,
            (0, horizon_y, inner_ai_rect.width, inner_ai_rect.height - horizon_y)
        )

        # Draw pitch ticks
        for deg in range(-90, 95, 5):  # pitch marks in degrees
            if deg == 0:
                width = 85
            elif deg % 10 == 0:
                width = 30
            else:
                width = 15

            y = horizon_y + deg * tick_spacing

            if 0 <= y <= inner_ai_rect.height:
                pg.draw.line(
                    ai_surface,
                    cols.WHITE,
                    (inner_ai_rect.width//2 - width, y),
                    (inner_ai_rect.width//2 + width, y),
                    3
                )

        cx = inner_ai_rect.width // 2
        top_y = 20
        bot_y = inner_ai_rect.height - 20
        chev_w = 18
        chev_h = 10

        # Nose too low -> point up
        if pitch >= C.CHEVRON_ANGLE:
            pg.draw.polygon(
                ai_surface, cols.WHITE,
                [
                    (cx - (chev_w+7), bot_y+2),
                    (cx + (chev_w+7), bot_y+2),
                    (cx, bot_y - (chev_h+2)),
                ]
            )
            pg.draw.polygon(
                ai_surface, C.CHEVRON_COLOUR,
                [
                    (cx - chev_w, bot_y),
                    (cx + chev_w, bot_y),
                    (cx, bot_y - chev_h),
                ]
            )
        # Nose too high -> point down
        elif pitch <= -C.CHEVRON_ANGLE:
            pg.draw.polygon(
                ai_surface, cols.WHITE,
                [
                    (cx - (chev_w+7), top_y-2),
                    (cx + (chev_w+7), top_y-2),
                    (cx, top_y + (chev_h+2)),
                ]
            )
            pg.draw.polygon(
                ai_surface, C.CHEVRON_COLOUR,
                [
                    (cx - chev_w, top_y),
                    (cx + chev_w, top_y),
                    (cx, top_y + chev_h),
                ]
            )

        rotated_ai = pg.transform.rotate(ai_surface, roll)
        rot_rect = rotated_ai.get_rect(center=(inner_ai_rect.width//2, inner_ai_rect.height//2))

        masked = pg.Surface(inner_ai_rect.size, pg.SRCALPHA)
        masked.blit(rotated_ai, rot_rect)
        masked.blit(self.ai_mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

        hud_surface.blit(masked, inner_ai_rect.topleft)

        # Inverted V-bar (should stay fixed to the HUD in a consistent position)
        pg.draw.line(hud_surface, (255, 255, 0), (ai_centre[0]-35, ai_centre[1]), (ai_centre[0]-15, ai_centre[1]), 3)
        pg.draw.line(hud_surface, (255, 255, 0), (ai_centre[0]+35, ai_centre[1]), (ai_centre[0]+15, ai_centre[1]), 3)
        pg.draw.line(hud_surface, (255, 255, 0), ai_centre, (ai_centre[0]-10, ai_centre[1]+5), 3)
        pg.draw.line(hud_surface, (255, 255, 0), ai_centre, (ai_centre[0]+10, ai_centre[1]+5), 3)

        # Cockpit warning lights
        warning_x = C.WN_W//2-180
        draw_text(hud_surface, (warning_x +20, C.WN_H*0.93), 'left', 'centre', "STALL", (25, 20, 18), 20, self.fonts.monospaced)
        warning_col = (255, 0, 0) if self.show_stall_warning else cols.BLACK
        pg.draw.circle(hud_surface, (51, 43, 37), (warning_x, C.WN_H*0.93), 10)
        pg.draw.circle(hud_surface, (warning_col), (warning_x, C.WN_H*0.93), 8)

        warning_x = C.WN_W//2-190  # Overspeed
        draw_text(hud_surface, (warning_x + 20, C.WN_H*0.965), 'left', 'centre', "OVERSPEED", (25, 20, 18), 20, self.fonts.monospaced)
        warning_col = (255, 0, 0) if self.show_overspeed_warning else cols.BLACK
        pg.draw.circle(hud_surface, (51, 43, 37), (warning_x, C.WN_H*0.965), 10)
        pg.draw.circle(hud_surface, (warning_col), (warning_x, C.WN_H*0.965), 8)

        # Render map
        if self.map_up:
            self.draw_map()

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
            draw_text(self.hud_surface, (C.WN_W//2, C.WN_H*0.35), 'centre', 'centre', 'CRASH', (255, 0, 0), 50, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2, C.WN_H*0.41), 'centre', 'centre', ui_text, (255, 255, 255), 30, self.fonts.monospaced)
            draw_text(self.hud_surface, (C.WN_W//2, C.WN_H*0.54), 'centre', 'centre', 'Press P to return to menu.', (255, 255, 255), 30, self.fonts.monospaced)

        # Show crash reason on screen
        if self.plane.crash_reason is not None:
            show_crash_reason(self.plane.crash_reason)

        # Upload HUD surface to OpenGL
        hud_data = pg.image.tostring(hud_surface, "RGBA", True)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.hud_tex)
        gl.glTexSubImage2D(
            gl.GL_TEXTURE_2D,
            0,
            0, 0,
            C.WN_W,
            C.WN_H,
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            hud_data
        )
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

    def draw(self, wn: Surface):
        colour_scheme = sky_colour_from_hour(fetch_hour())

        gl.glClear(cast(int, gl.GL_COLOR_BUFFER_BIT) | cast(int, gl.GL_DEPTH_BUFFER_BIT))

        # Draw sky gradient background
        self.sky.draw(colour_scheme)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        # Apply camera transformations based on plane's state
        # The order of operations is Yaw, then Pitch, then Roll.
        # OpenGL applies matrix transformations in reverse order of the calls.
        gl.glRotatef(self.plane.rot.z, 0, 0, 1) # 3. Roll
        gl.glRotatef(self.plane.rot.x, 1, 0, 0) # 2. Pitch
        gl.glRotatef(self.plane.rot.y, 0, 1, 0) # 1. Yaw

        camera_y = self.plane.pos.y + C.CAMERA_RADIUS
        gl.glTranslatef(-self.plane.pos.x, -camera_y, -self.plane.pos.z)

        pitch, yaw, _ = self.plane.rot
        camera_fwd = pg.Vector3(
            sin(rad(yaw)) * cos(rad(pitch)),
            sin(rad(-pitch)),  # pitch is negated since +pitch = nose down
            -cos(rad(yaw)) * cos(rad(pitch)),
        ).normalize()

        for star in self.env.stars:
            star.draw(camera_fwd)

        self.sun.draw()
        self.moon.draw()

        self.ground.draw()
        self.ocean.draw()

        for runway in self.env.runways:
            runway.draw()

        self.draw_buildings()
        self.draw_hud()
