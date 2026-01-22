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

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, cast

import pygame as pg
from OpenGL import GL as gl
from OpenGL import GLU as glu

import pylines.core.colours as cols
import pylines.core.constants as C
from pylines.core.custom_types import AColour, Colour, EventList, RealNumber
from pylines.core.time_manager import fetch_hour, sky_colour_from_hour
from pylines.core.units import FEET, METRES, convert_units
from pylines.core.utils import clamp, draw_needle, draw_text, draw_transparent_rect
from pylines.game.engine_sound import SoundManager
from pylines.game.states import State
from pylines.objects.objects import CrashReason, Plane, Runway
from pylines.objects.scenery import Ground, Moon, Ocean, Sky, Sun

if TYPE_CHECKING:
    from pylines.core.custom_types import ScancodeWrapper, Surface
    from pylines.game.game import Game

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
        self.landing_dialog_box = DialogMessage()  # Must be before Plane otherwise causes error
        self.sound_manager = SoundManager(assets.sounds)

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

        self.plane = Plane(assets.sounds, self.landing_dialog_box, game.env)
        self.sky = Sky()
        self.sun = Sun(assets.images.sun)
        self.moon = Moon(assets.images.moon)
        self.show_stall_warning: bool = False
        self.show_overspeed_warning: bool = False
        self.time_elapsed: int = 0  # milliseconds

        self.stall_channel = pg.mixer.Channel(3)
        self.overspeed_channel = pg.mixer.Channel(4)

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

        def height_to_colour(h: RealNumber):
            THRESHOLDS: dict[RealNumber, Colour] = {
                5750: (207, 238, 255),
                5300: (131, 134, 136),
                4000: (64, 64, 64),
                2200: (110, 67, 41),
                800: (35, 110, 35),
                150: (45, 170, 45),
                0: (240, 240, 190),
                -200: (0, 180, 240),
            }

            for th, col in THRESHOLDS.items():
                if h > th:
                    return col
            return (0, 126, 199)

        # Initialise minimap
        WORLD_STEP = 2*C.WORLD_SIZE // C.MINIMAP_SIZE
        self.minimap = pg.Surface((C.MINIMAP_SIZE, C.MINIMAP_SIZE))
        px = pg.PixelArray(self.minimap)
        for z_i, z in enumerate(range(-C.WORLD_SIZE, C.WORLD_SIZE, WORLD_STEP)):
            for x_i, x in enumerate(range(-C.WORLD_SIZE, C.WORLD_SIZE, WORLD_STEP)):
                px[x_i, z_i] = height_to_colour(self.game.env.height_at(x, z))  # type: ignore[index]
        del px

    def reset(self) -> None:
        self.plane.reset()
        self.sound_manager.stop()
        self.overspeed_channel.stop()
        self.sounds.menu_music.fadeout(1_500)
        self.landing_dialog_box.reset()
        self.time_elapsed = 0

    def update(self, dt: int):
        self._frame_count += 1
        self.time_elapsed += dt
        self.landing_dialog_box.update(dt)

        self.sun.update()
        self.moon.update()

        if self.plane.crashed:
            self.landing_dialog_box.reset()
            self.stall_channel.stop()
            self.overspeed_channel.stop()
            self.sound_manager.stop()
            return

        self.sound_manager.update(self.plane.throttle_frac)
        self.plane.update(dt)

        self.show_stall_warning = self.plane.stalled
        if self.show_stall_warning:
            if not self.stall_channel.get_busy():
                self.stall_channel.play(self.sounds.stall_warning, loops=-1)
        else:
            self.stall_channel.stop()

        self.show_overspeed_warning = self.plane.vel.length() > self.plane.model.v_ne  # Both in m/s
        if self.show_overspeed_warning:
            if not self.overspeed_channel.get_busy():
                self.overspeed_channel.play(self.sounds.overspeed, loops=-1)
        else:
            self.overspeed_channel.stop()

    def _draw_text(self, x: RealNumber, y: RealNumber, text: str,
                  colour: AColour = (255, 255, 255, 255), bg_colour: AColour | None = None):
        if bg_colour is None:
            text_surface = self.font.render(text, True, colour)
        else:
            text_surface = self.font.render(text, True, colour, bg_colour)
        text_surface = pg.transform.flip(text_surface, False, True) # Flip vertically
        text_data = pg.image.tostring(text_surface, "RGBA", True)

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        glu.gluOrtho2D(0, C.WN_W, C.WN_H, 0)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        texid = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texid)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, text_surface.get_width(), text_surface.get_height(), 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, text_data)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)

        gl.glBegin(gl.GL_QUADS)
        gl.glTexCoord2f(0, 0); gl.glVertex2f(x, y)
        gl.glTexCoord2f(1, 0); gl.glVertex2f(x + text_surface.get_width(), y)
        gl.glTexCoord2f(1, 1); gl.glVertex2f(x + text_surface.get_width(), y + text_surface.get_height())
        gl.glTexCoord2f(0, 1); gl.glVertex2f(x, y + text_surface.get_height())
        gl.glEnd()

        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_BLEND)
        gl.glDeleteTextures(1, [texid])

        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        # Meta controls
        if self.pressed(keys, pg.K_p):
            self.sounds.menu_music.stop()
            self.game.enter_state(self.game.States.TITLE)
            self.sound_manager.stop()
        if self.pressed(keys, pg.K_r):  # r to reset
            self.plane.reset()
            self.gps_runway_index = 1  # reset gps waypoint

        # Block flight controls if crashed or disabled
        if not self.plane.flyable:
            self.update_prev_keys(keys)
            return

        # Cycle GPS waypoint
        if self.pressed(keys, pg.K_g):
            self.gps_runway_index = (self.gps_runway_index + 1) % len(self.env.runways)

        # Throttle controls
        throttle_speed = 0.4 * dt/1000
        if keys[pg.K_w]:
            self.plane.throttle_frac += throttle_speed
        if keys[pg.K_s]:
            self.plane.throttle_frac -= throttle_speed
        self.plane.throttle_frac = clamp(self.plane.throttle_frac, (0, 1))

        base_rot_accel = 20 * dt/1000
        control_authority = 1 - 0.875 * self.plane.damage_level**2  # reduce authority based on damage level
        speed_authority_factor = clamp((self.plane.vel.length()/30.87)**2, (0.01, 1))  # based on vel in m/s
        rot_accel = control_authority * base_rot_accel * speed_authority_factor * (0.2 if self.plane.on_ground else 1)

        # Pitch
        if keys[pg.K_UP]:
            self.plane.rot_rate.x += rot_accel * (1 - (self.plane.rot.x / 90))
        if keys[pg.K_DOWN]:
            self.plane.rot_rate.x -= rot_accel * (1 + (self.plane.rot.x / 90))
        if not (keys[pg.K_UP] or keys[pg.K_DOWN]):
            self.plane.rot_rate.x *= (1 - 0.8 * dt/1000)

        # Turning
        if keys[pg.K_LEFT]:
            self.plane.rot_rate.z -= rot_accel
        if keys[pg.K_RIGHT]:
            self.plane.rot_rate.z += rot_accel
        if not (keys[pg.K_LEFT] or keys[pg.K_RIGHT]):
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
            f"{convert_units(altitude_agl, METRES, FEET):,.0f} ft",
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

        # Minimap
        mini_centre = (int(C.WN_W*0.1), int(C.WN_H*0.88))
        outer_mini_size = C.MINIMAP_SIZE + 6
        mini_rect = pg.Rect(0, 0, outer_mini_size, outer_mini_size)
        mini_rect.center = mini_centre
        pg.draw.rect(hud_surface, (51, 43, 37), mini_rect)
        mini_top_left = (mini_centre[0]-(C.MINIMAP_SIZE)/2, mini_centre[1]-(C.MINIMAP_SIZE)/2)
        hud_surface.blit(self.minimap, mini_top_left)

        px, pz = self.plane.pos.x, self.plane.pos.z
        cursor_coord = pg.Vector2(
            mini_centre[0] + (C.MINIMAP_SIZE/2)*(px/C.WORLD_SIZE),
            mini_centre[1] + (C.MINIMAP_SIZE/2)*(pz/C.WORLD_SIZE)
        )

        rotated_cursor = pg.transform.rotate(self.game.assets.images.minimap_cursor, -self.plane.rot.y)
        cursor_rect = rotated_cursor.get_rect(center=cursor_coord)
        hud_surface.blit(rotated_cursor, cursor_rect)

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

        # Show landing feedback
        if self.landing_dialog_box.active_time:
            draw_transparent_rect(
                self.hud_surface, (C.WN_W//2-300, C.WN_H*0.15), (600, C.WN_H*0.1), (0, 0, 0, 180), 2
            )
            draw_text(
                self.hud_surface, (C.WN_W//2, C.WN_H*0.2), 'centre', 'centre',
                self.landing_dialog_box.msg, self.landing_dialog_box.colour, 30, self.fonts.monospaced
            )

        def show_crash_reason(reason: CrashReason) -> None:
            if reason == CrashReason.TERRAIN:
                ui_text = "COLLISION WITH TERRAIN"
            elif reason == CrashReason.OCEAN:
                ui_text = "COLLISION WITH OCEAN"
            elif reason == CrashReason.BUILDING:
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

        self.sun.draw()
        self.moon.draw()

        for runway in self.env.runways:
            runway.draw()

        for building in self.env.buildings:
            building.draw()

        self.ground.draw()
        self.ocean.draw()
        self.draw_hud()
