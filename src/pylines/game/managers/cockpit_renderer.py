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

import math
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, cast

import pygame as pg

import pylines.core.colours as cols
import pylines.core.constants as C
import pylines.core.units as units
from pylines.core.custom_types import AColour, Colour, Surface
from pylines.core.utils import clamp, draw_needle, draw_text, frange, get_lerp_weight
from pylines.objects.objects import Plane
from pylines.objects.scenery.runway import Runway

if TYPE_CHECKING:
    from pylines.game.game import Game
    from pylines.objects.objects import Plane

class CockpitRenderer:
    def __init__(self, game: Game, plane: Plane) -> None:
        self.game = game  # Must be done before populating the static surface
        self.plane = plane

        # Setup persistent surfaces
        self.cockpit_rect = self.game.assets.images.cockpit.get_bounding_rect()
        self.crash_colour_fade_surface: Surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
        self.static_cached_surface: Surface = self.populate_static_surface()

        # Setup attitude indicator mask
        ai_size = 170, 170
        inner_ai_rect = pg.Rect(0, 0, ai_size[0]-4, ai_size[1]-4)
        self.ai_mask = pg.Surface(inner_ai_rect.size, pg.SRCALPHA)
        pg.draw.circle(
            self.ai_mask,
            cols.WHITE,
            (inner_ai_rect.width//2, inner_ai_rect.height//2),
            inner_ai_rect.width//2
        )

        # Cache attitude indicator display to avoid wasteful label drawing
        self.cached_ai_surface = self.populate_ai_surface()
        inner_ai_rect = pg.Rect(0, 0, ai_size[0]-4, ai_size[1]-4)
        self.ai_surface = pg.Surface(inner_ai_rect.size, pg.SRCALPHA)

        # Cache compasses to avoid wasteful per-frame rotations
        self.rotated_compasses: list[pg.Surface] = [
            pg.transform.rotate(self.game.assets.images.compass, theta)
            for theta in frange(0, 360, 360/C.COMPASS_QUANTISATION_STEPS)
        ]

    def populate_ai_surface(self) -> Surface:
        width = 170 - 4
        height = 2000
        surface = pg.Surface((width, height), pg.SRCALPHA)
        surface.fill((0, 0, 0, 0))

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
                    surface,
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
                        surface, (width//2 + line_width + 5, y), 'left', 'centre',
                        str(abs(deg_display_value)), cols.WHITE, 19, self.game.assets.fonts.monospaced
                    )
                    draw_text(
                        surface, (width//2 - line_width - 5, y), 'right', 'centre',
                        str(abs(deg_display_value)), cols.WHITE, 19, self.game.assets.fonts.monospaced
                    )

        return surface

    def populate_static_surface(self) -> Surface:
        """Populates a static surface for drawing static elements to avoid
        wasteful redraws."""

        surface = pg.Surface((C.WN_W, C.WN_H), flags=pg.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        # Cockpit background
        cockpit = self.game.assets.images.cockpit
        surface.blit(cockpit, (0, C.WN_H - self.cockpit_rect.height))

        # Speed dial (static background)
        speed_centre = (C.WN_W//2+300, C.WN_H*0.85)
        rect = self.game.assets.images.speed_dial.get_rect(center=speed_centre)
        surface.blit(self.game.assets.images.speed_dial, rect)

        # Altimeter static boxes
        alt_centre = (C.WN_W//2 - 110, int(C.WN_H*0.74))
        alt_size = 160, 70
        alt_rect = pg.Rect(0, 0, *alt_size)
        alt_rect.center = alt_centre
        pg.draw.rect(surface, cols.WHITE, alt_rect)
        inner_alt_rect = pg.Rect(0, 0, alt_size[0]-4, alt_size[1]-4)
        inner_alt_rect.center = alt_centre
        pg.draw.rect(surface, cols.BLACK, inner_alt_rect)

        # Location static boxes
        loc_centre = (C.WN_W//2 + 85, int(C.WN_H*0.74))
        loc_size = 210, 70
        loc_rect = pg.Rect(0, 0, *loc_size)
        loc_rect.center = loc_centre
        pg.draw.rect(surface, cols.WHITE, loc_rect)
        inner_loc_rect = pg.Rect(0, 0, loc_size[0]-4, loc_size[1]-4)
        inner_loc_rect.center = loc_centre
        pg.draw.rect(surface, cols.BLACK, inner_loc_rect)

        # Time readout static boxes
        time_centre = (C.WN_W//2 - 130, int(C.WN_H*0.81))
        time_size = 100, 30
        time_rect = pg.Rect(0, 0, *time_size)
        time_rect.center = time_centre
        pg.draw.rect(surface, cols.WHITE, time_rect)
        inner_time_rect = pg.Rect(0, 0, time_size[0]-4, time_size[1]-4)
        inner_time_rect.center = time_centre
        pg.draw.rect(surface, cols.BLACK, inner_time_rect)

        # AGL readout static boxes + label
        agl_centre = (C.WN_W//2 + 130, int(C.WN_H*0.81))
        agl_size = 100, 30
        agl_rect = pg.Rect(0, 0, *agl_size)
        agl_rect.center = agl_centre
        pg.draw.rect(surface, cols.WHITE, agl_rect)
        inner_agl_rect = pg.Rect(0, 0, agl_size[0]-4, agl_size[1]-4)
        inner_agl_rect.center = agl_centre
        pg.draw.rect(surface, cols.BLACK, inner_agl_rect)
        draw_text(
            surface, (agl_centre[0] - 45, agl_centre[1]), 'left', 'centre',
            "AGL", cols.WHITE, 12, self.game.assets.fonts.monospaced
        )

        # GPS static boxes
        gps_centre = (C.WN_W//2 - 135, int(C.WN_H*0.87))
        gps_size = 80, 60
        gps_rect = pg.Rect(0, 0, *gps_size)
        gps_rect.center = gps_centre
        pg.draw.rect(surface, cols.WHITE, gps_rect)
        inner_gps_rect = pg.Rect(0, 0, gps_size[0]-4, gps_size[1]-4)
        inner_gps_rect.center = gps_centre
        pg.draw.rect(surface, cols.BLACK, inner_gps_rect)

        # Glidescope frame
        glide_centre = (C.WN_W//2 + 105, int(C.WN_H*0.91))
        glide_size = 18, 125
        glide_rect = pg.Rect(0, 0, *glide_size)
        glide_rect.center = glide_centre
        pg.draw.rect(surface, cols.WHITE, glide_rect)
        inner_glide_rect = pg.Rect(0, 0, glide_size[0]-4, glide_size[1]-4)
        inner_glide_rect.center = glide_centre
        pg.draw.rect(surface, cols.BLACK, inner_glide_rect)

        # Throttle rail + label
        draw_text(surface, (C.WN_W*0.86, C.WN_H*0.97), 'centre', 'centre', "Throttle", (25, 20, 18), 30, self.game.assets.fonts.monospaced)
        pg.draw.line(surface, (51, 43, 37), (C.WN_W*0.86, C.WN_H*0.94), (C.WN_W*0.86, C.WN_H*0.75), 3)

        # Flaps rail
        pg.draw.line(surface, (51, 43, 37), (C.WN_W*0.90, C.WN_H*0.93), (C.WN_W*0.90, C.WN_H*0.76), 3)

        # Attitude indicator static ring
        ai_centre = (C.WN_W//2, int(C.WN_H*0.89))
        pg.draw.circle(surface, cols.WHITE, ai_centre, 85)

        # Cockpit warning light labels + sockets
        warning_x = C.WN_W//2-180
        draw_text(surface, (warning_x + 20, C.WN_H*0.93), 'left', 'centre', "STALL", (25, 20, 18), 20, self.game.assets.fonts.monospaced)
        pg.draw.circle(surface, (51, 43, 37), (warning_x, C.WN_H*0.93), 10)

        warning_x = C.WN_W//2-190
        draw_text(surface, (warning_x + 20, C.WN_H*0.965), 'left', 'centre', "OVERSPEED", (25, 20, 18), 20, self.game.assets.fonts.monospaced)
        pg.draw.circle(surface, (51, 43, 37), (warning_x, C.WN_H*0.965), 10)

        return surface

    def draw(self, surface: Surface, warn_stall: bool, warn_overspeed: bool) -> None:
        assert self.game.env is not None

        # Crash colour fade and smoke - should be behind other UI elements but
        # infront of scenery
        if self.plane.crashed:
            assert self.plane.time_since_lethal_crash is not None

            # Draw smoke
            self.game.smoke_manager.draw_smoke_blobs(surface)

            # Clear colour fade surface
            self.crash_colour_fade_surface.fill((0, 0, 0, 0))

            colour: cols.AColour
            if self.plane.time_since_lethal_crash < 1:
                colour = cols.lerp_colours((255, 255, 255, 255), (255, 180, 100, 255), self.plane.time_since_lethal_crash)
            elif self.plane.time_since_lethal_crash < 2:
                colour = cols.lerp_colours((255, 180, 100, 255), (220, 40, 40, 100), self.plane.time_since_lethal_crash - 1)
            elif self.plane.time_since_lethal_crash < 3:
                colour = cols.lerp_colours((220, 40, 40, 100), (0, 0, 0, 0), self.plane.time_since_lethal_crash - 2)
            else:
                colour = (0, 0, 0, 0)

            self.crash_colour_fade_surface.fill(colour)  # Fill should be infront of smoke
            surface.blit(self.crash_colour_fade_surface, (0, 0))

        # Setup
        pitch, yaw, roll = self.plane.get_rot()

        # Stall warning
        warning_x = C.WN_W//2-145
        if warn_stall:
            draw_text(surface, (C.WN_W//2, C.WN_H*0.62), 'centre', 'centre', "STALL", (210, 0, 0), 50, self.game.assets.fonts.monospaced)

        # Overspeed warning
        warning_x = C.WN_W//2+145
        if warn_overspeed:
            draw_text(surface, (C.WN_W//2, C.WN_H*0.57), 'centre', 'centre', "OVERSPEED", (210, 0, 0), 50, self.game.assets.fonts.monospaced)

        # Damage overlay
        if self.plane.damage_level > 0:
            overlays = self.game.assets.images.damage_overlays
            # Damage_level is 0-1, so we can map it to the number of overlays
            overlay_idx = min(len(overlays) - 1, int(self.plane.damage_level * (len(overlays))))
            overlay = overlays[overlay_idx]
            surface.blit(overlay, (0, 0))

        # Static cockpit surface
        surface.blit(self.static_cached_surface, (0, C.WN_H - self.static_cached_surface.get_rect().height))

        # Compass (heading + ground track)
        centre = (C.WN_W//2-300, C.WN_H*0.85)
        surf = self.rotated_compasses[int(yaw / (360 / C.COMPASS_QUANTISATION_STEPS))]
        rect = surf.get_rect(center=centre)
        surface.blit(surf, rect)

        vel_flat = pg.Vector3(self.plane.vel.x, 0, self.plane.vel.z)
        ground_track_deg = math.degrees(
            math.atan2(vel_flat.x, -vel_flat.z)
        ) % 360 if vel_flat.length() >= C.MATH_EPSILON else 0

        selected_runway: Runway = self.game.env.runways[self.plane.gps_runway_index]
        gps_distance = selected_runway.pos - self.plane.pos
        gps_distance_flat = pg.Vector3(gps_distance.x, 0, gps_distance.z)
        gps_bearing = math.degrees(
            math.atan2(gps_distance_flat.x, -gps_distance_flat.z)
        ) % 360 if gps_distance_flat.length() >= C.MATH_EPSILON else 0

        # Ground track (the actual velocity vector of the plane)
        draw_needle(surface, centre, 90 - (ground_track_deg-yaw), 100, (255, 190, 0))
        # Heading (where the nose points)
        draw_needle(surface, centre, 90, 100, (255, 0, 0))
        # GPS distance (where the nose points)
        draw_needle(surface, centre, 90 - (gps_bearing-yaw), 100, (0, 255, 0))

        # Show runway alignment (blue needle)
        if gps_distance_flat.length() < 8000:
            draw_needle(surface, centre, 90 - (selected_runway.heading-yaw), 50, (0, 120, 255))
            draw_needle(surface, centre, 270 - (selected_runway.heading-yaw), 50, (0, 120, 255))

        # ASI (Airspeed Indicator)
        centre = (C.WN_W//2+300, C.WN_H*0.85)
        speed_knots = self.plane.vel.length() * 1.94384  # Convert to knots
        angle = 90 - min(336, 270 * speed_knots/160)
        draw_text(
            surface, (C.WN_W//2+300, C.WN_H*0.85 + 30), 'centre', 'centre',
            f"{int(self.plane.vel.length() * 1.94384):03d}", (192, 192, 192), 35, self.game.assets.fonts.monospaced
        )
        draw_needle(surface, centre, angle, 100)

        # Altimeter (left)
        alt_centre = (C.WN_W//2 - 110, int(C.WN_H*0.74))
        draw_text(
            surface, (alt_centre[0], alt_centre[1]-15), 'centre', 'centre',
            f"{self.plane.pos.y * 3.28084:,.0f} ft", cols.WHITE, 27, self.game.assets.fonts.monospaced
        )

        # VSI (below altimeter)
        vsi_centre = (alt_centre[0], alt_centre[1]+15)
        vs_ft_per_min = self.plane.vel.y * 196.85
        text_colour: Colour = cols.BLUE if vs_ft_per_min > 0 else cols.WHITE if vs_ft_per_min == 0 else cols.BROWN
        draw_text(
            surface, vsi_centre, 'centre', 'centre',
            f"{vs_ft_per_min:+,.0f}/min", text_colour, 22, self.game.assets.fonts.monospaced
        )

        # Location / LOC (right)
        loc_centre = (C.WN_W//2 + 85, int(C.WN_H*0.74))
        draw_text(
            surface, loc_centre, 'centre', 'centre',
            f"({self.plane.pos.x:,.0f}m, {self.plane.pos.z:,.0f}m)", cols.WHITE, 22, self.game.assets.fonts.monospaced
        )

        # Time readout
        time_centre = (C.WN_W//2 - 130, int(C.WN_H*0.81))

        now = datetime.now().astimezone()
        offset_hours = int(cast(timedelta, now.utcoffset()).total_seconds() // 3600)
        draw_text(
            surface, time_centre, 'centre', 'centre',
            f"{now.hour:02d}:{now.minute:02d} ({offset_hours:+d})", cols.WHITE, 18, self.game.assets.fonts.monospaced
        )

        # AGL readout
        agl_centre = (C.WN_W//2 + 130, int(C.WN_H*0.81))
        x, z = self.plane.pos.x, self.plane.pos.z
        altitude_agl = self.plane.pos.y - self.game.env.get_ground_height(x, z)
        draw_text(
            surface, (agl_centre[0] + 45, agl_centre[1]), 'right', 'centre',
            f"{units.convert_units(altitude_agl, units.METRES, units.FEET):,.0f} ft", cols.WHITE, 18, self.game.assets.fonts.monospaced
        )

        # GPS information
        gps_centre = (C.WN_W//2 - 135, int(C.WN_H*0.87))

        draw_text(
            surface, (gps_centre[0] - 35, gps_centre[1] - 14),
            'left', 'centre', selected_runway.name, (0, 120, 255), 20, self.game.assets.fonts.monospaced
        )

        draw_text(
            surface, (gps_centre[0] - 35, gps_centre[1] + 14),
            'left', 'centre', f"{gps_distance_flat.length() / 1000:,.2f}km", cols.WHITE, 20, self.game.assets.fonts.monospaced
        )

        # Glidescope
        glide_centre = (C.WN_W//2 + 105, int(C.WN_H*0.91))

        # Compute comparison for glidescope
        GLIDEPATH_SLOPE = math.tan(math.radians(3.0))  # glidescope is 3°
        expected_height_above_runway = gps_distance_flat.length() * GLIDEPATH_SLOPE
        expected_height_msl = expected_height_above_runway + selected_runway.pos.y
        deviation = self.plane.pos.y - expected_height_msl

        # Display glidescope
        show_glidescope = (
            gps_distance_flat.length() < 5_000 and  # runway is close
            self.plane.pos.y > self.game.env.get_ground_height(self.plane.pos.x, self.plane.pos.z)  # plane is still in the air
        )

        if show_glidescope:
            glide_centre_x, glide_centre_y = glide_centre

            # Tick marks
            pg.draw.line(surface, (140, 140, 140), (glide_centre_x-7, glide_centre_y + 26), (glide_centre_x+6, glide_centre_y + 26), 2)
            pg.draw.line(surface, (140, 140, 140), (glide_centre_x-7, glide_centre_y + 52), (glide_centre_x+6, glide_centre_y + 52), 2)
            pg.draw.line(surface, (140, 140, 140), (glide_centre_x-7, glide_centre_y - 26), (glide_centre_x+6, glide_centre_y - 26), 2)
            pg.draw.line(surface, (140, 140, 140), (glide_centre_x-7, glide_centre_y - 52), (glide_centre_x+6, glide_centre_y - 52), 2)

            # Green circle
            pg.draw.circle(surface, (0, 255, 0), (glide_centre_x, glide_centre_y + clamp(deviation, (-10, 10)) * 52/10), 5)

            # White line
            pg.draw.line(surface, cols.WHITE, (glide_centre_x-7, glide_centre_y), (glide_centre_x+6, glide_centre_y), 2)


        # Throttle bar
        size = 40, 20
        rect = pg.Rect(0, 0, *size)
        rect.center = (C.WN_W*0.86, C.WN_H*0.94 - C.WN_H*0.19*(self.plane.throttle_frac))  # type: ignore[arg-type]
        pg.draw.rect(surface, cols.WHITE, rect)

        # Flaps indicator
        size = 30, 15
        rect = pg.Rect(0, 0, *size)
        rect.center = (C.WN_W*0.90, C.WN_H*0.93 - C.WN_H*0.17*(self.plane.flaps))  # type: ignore[arg-type]
        pg.draw.rect(surface, (220, 220, 220), rect)

        # Attitude indicator
        self.ai_surface.fill((0, 0, 0, 0))  # clear AI surface
        ai_centre = (C.WN_W//2, int(C.WN_H*0.89))
        ai_size = 170, 170
        ai_rect = pg.Rect(0, 0, *ai_size)
        ai_rect.center = ai_centre
        inner_ai_rect = pg.Rect(0, 0, ai_size[0]-4, ai_size[1]-4)
        inner_ai_rect.center = ai_centre

        tick_spacing = 5  # pixels per 5° of pitch

        # Normalize for inverted flight: keep horizon "true" and flip roll markers
        pitch_display = pitch
        roll_display = roll
        if pitch > 90:
            pitch_display = 180 - pitch
            roll_display += 180
        elif pitch < -90:
            pitch_display = -180 - pitch
            roll_display += 180
        roll_display = (roll_display + 180) % 360 - 180

        # Horizon position (in local AI coords)
        horizon_y = inner_ai_rect.height // 2 - pitch_display * tick_spacing

        # Sky (above horizon)
        pg.draw.rect(
            self.ai_surface,
            cols.DARK_BLUE,
            (0, 0, inner_ai_rect.width, horizon_y)
        )

        # Ground (below horizon)
        pg.draw.rect(
            self.ai_surface,
            cols.DARK_BROWN,
            (0, horizon_y, inner_ai_rect.width, inner_ai_rect.height - horizon_y)
        )

        cached_center_y = self.cached_ai_surface.get_height() // 2
        self.ai_surface.blit(
            self.cached_ai_surface,
            (0, horizon_y - cached_center_y),
        )

        cx = inner_ai_rect.width // 2
        top_y = 20
        bot_y = inner_ai_rect.height - 20
        chev_w = 18
        chev_h = 10

        # Nose too low -> point up
        if pitch_display >= C.CHEVRON_ANGLE:
            pg.draw.polygon(
                self.ai_surface, cols.WHITE,
                [
                    (cx - (chev_w+7), bot_y+2),
                    (cx + (chev_w+7), bot_y+2),
                    (cx, bot_y - (chev_h+2)),
                ]
            )
            pg.draw.polygon(
                self.ai_surface, C.CHEVRON_COLOUR,
                [
                    (cx - chev_w, bot_y),
                    (cx + chev_w, bot_y),
                    (cx, bot_y - chev_h),
                ]
            )
        # Nose too high -> point down
        elif pitch_display <= -C.CHEVRON_ANGLE:
            pg.draw.polygon(
                self.ai_surface, cols.WHITE,
                [
                    (cx - (chev_w+7), top_y-2),
                    (cx + (chev_w+7), top_y-2),
                    (cx, top_y + (chev_h+2)),
                ]
            )
            pg.draw.polygon(
                self.ai_surface, C.CHEVRON_COLOUR,
                [
                    (cx - chev_w, top_y),
                    (cx + chev_w, top_y),
                    (cx, top_y + chev_h),
                ]
            )

        rotated_ai = pg.transform.rotate(self.ai_surface, roll_display)
        rot_rect = rotated_ai.get_rect(center=(inner_ai_rect.width//2, inner_ai_rect.height//2))

        masked = pg.Surface(inner_ai_rect.size, pg.SRCALPHA)
        masked.blit(rotated_ai, rot_rect)
        masked.blit(self.ai_mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

        surface.blit(masked, inner_ai_rect.topleft)

        # Static V-bar for AI must be drawn in draw_cockpit as
        # it is infront of the artificial horizon overlay
        inverted = (
            (90 < roll % 360 < 270) and (-90 < pitch < 90)
            or ((roll % 360 > 270 or roll % 360 < 90) and (pitch > 90 or pitch < -90))
        )

        ai_centre = (C.WN_W//2, int(C.WN_H*0.89))

        # The two yellow lines either side of the V-bar
        pg.draw.line(surface, (255, 255, 0), (ai_centre[0]-35, ai_centre[1]), (ai_centre[0]-15, ai_centre[1]), 3)
        pg.draw.line(surface, (255, 255, 0), (ai_centre[0]+35, ai_centre[1]), (ai_centre[0]+15, ai_centre[1]), 3)

        # V-bar itself, draw as inverted if plane is inverted, so it always "points" in the direction of the nose
        if not inverted:
            pg.draw.line(surface, (255, 255, 0), ai_centre, (ai_centre[0]-10, ai_centre[1]+5), 3)
            pg.draw.line(surface, (255, 255, 0), ai_centre, (ai_centre[0]+10, ai_centre[1]+5), 3)
        else:
            pg.draw.line(surface, (255, 255, 0), ai_centre, (ai_centre[0]-10, ai_centre[1]-5), 3)
            pg.draw.line(surface, (255, 255, 0), ai_centre, (ai_centre[0]+10, ai_centre[1]-5), 3)

            # Show text "INV" below the V-bar to indicate inverted flight, as it can be easy to miss otherwise
            draw_text(
                surface, (ai_centre[0], ai_centre[1]+20), 'centre', 'centre',
                "INV", (255, 255, 0), 18, self.game.assets.fonts.monospaced
            )

        # Cockpit warning lights
        warning_x = C.WN_W//2-180
        warning_col = (255, 0, 0) if warn_stall else cols.BLACK
        pg.draw.circle(surface, (warning_col), (warning_x, C.WN_H*0.93), 8)

        warning_x = C.WN_W//2-190  # Overspeed
        warning_col = (255, 0, 0) if warn_overspeed else cols.BLACK
        pg.draw.circle(surface, (warning_col), (warning_x, C.WN_H*0.965), 8)

    def draw_crash_flash(self, surface: Surface) -> None:
        # This is a separate funtion as it needs to be drawn on
        # top of some UI elements.

        if self.plane.time_since_lethal_crash is None:
            return  # Skip drawing if the plane hasn't crashed

        colour: AColour
        if self.plane.time_since_lethal_crash < 0.75:
            colour = cols.lerp_colours((255, 255, 255, 140), (255, 234, 166, 70), get_lerp_weight(self.plane.time_since_lethal_crash, 0, 0.75))
        elif self.plane.time_since_lethal_crash < 1.5:
            colour = cols.lerp_colours((255, 234, 166, 70), (0, 0, 0, 0), get_lerp_weight(self.plane.time_since_lethal_crash, 0.75, 1.5))
        else:
            colour = (0, 0, 0, 0)

        self.crash_colour_fade_surface.fill(colour)
        surface.blit(self.crash_colour_fade_surface, (0, 0))