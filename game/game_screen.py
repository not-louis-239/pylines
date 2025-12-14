from __future__ import annotations
from typing import TYPE_CHECKING, cast
import math

import pygame as pg

from core.colours import SKY_COLOUR_SCHEMES, BLUE, WHITE, BROWN, DARK_BLUE, DARK_BROWN
from core.custom_types import RealNumber, AColour, Colour
import core.constants as C
from core.utils import clamp, draw_needle, draw_text
from game.state_management import State
from objects.objects import Plane
from objects.scenery import Sky, Ground
import OpenGL.GL as gl
import OpenGL.GLU as glu

if TYPE_CHECKING:
    from core.custom_types import Surface, ScancodeWrapper
    from game.game import Game

class GameScreen(State):
    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.plane = Plane(game.assets.sounds)
        self.ground = Ground(game.assets.images.test_grass)  # Pass the loaded image to Ground
        self.sky = Sky()
        self.time_of_day: str = "sunset"
        self.show_stall_warning: bool = False

        self.stall_channel = pg.mixer.Channel(3)

        # Font for text rendering
        self.font = pg.font.Font(game.assets.fonts.monospaced, 36)

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

    def reset(self) -> None:
        self.plane.reset()
        self.sounds.menu_music.stop()

    def update(self, dt: int):
        self.plane.update(dt)

        self.show_stall_warning = self.plane.aoa > self.plane.model.stall_angle

        if self.show_stall_warning:
            if not self.stall_channel.get_busy():
                self.stall_channel.play(self.sounds.stall_warning, loops=-1)
        else:
            self.stall_channel.stop()

        if self.plane.crashed:
            self.game.enter_state('title')

    def draw_text(self, x: RealNumber, y: RealNumber, text: str,
                  colour: AColour = (255, 255, 255, 255), bg_colour: AColour | None = None):  # FIXME: no workie!
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

    def take_input(self, keys: ScancodeWrapper, dt: int) -> None:
        rot_speed = 20 * dt/1000
        throttle_speed = 0.5 * dt/1000

        # Throttle
        if keys[pg.K_w]:
            self.plane.throttle_frac += throttle_speed
        if keys[pg.K_s]:
            self.plane.throttle_frac -= throttle_speed

        # Clamp throttle
        self.plane.throttle_frac = clamp(self.plane.throttle_frac, 0, 1)

        # Pitch
        if keys[pg.K_UP]:
            self.plane.rot.x -= rot_speed * (1+(self.plane.rot.x/90))
        if keys[pg.K_DOWN]:
            self.plane.rot.x += rot_speed * (1-(self.plane.rot.x/90))
        # Turning (Roll)
        if keys[pg.K_LEFT]:
            self.plane.rot.z -= rot_speed
        if keys[pg.K_RIGHT]:
            self.plane.rot.z += rot_speed

        # Clamp
        self.plane.rot.y %= 360
        self.plane.rot.z %= 360
        self.plane.rot.x = clamp(self.plane.rot.x, -90, 90)

    def draw_hud(self):
        pitch, yaw, roll = self.plane.rot
        hud_surface = self.hud_surface
        hud_surface.fill((0, 0, 0, 0))  # clear with transparency

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

        vel_flat = pg.Vector2(self.plane.vel.x, self.plane.vel.z)
        ground_track_deg = math.degrees(
            math.atan2(vel_flat.x, -vel_flat.y)
        ) % 360 if vel_flat.length() >= C.EPSILON else 0

        # Ground track (the actual velocity vector of the plane)
        draw_needle(hud_surface, centre, 90 - (ground_track_deg-yaw), 100, (255, 190, 0))
        # Heading (where the nose points)
        draw_needle(hud_surface, centre, 90, 100)

        # ASI (Air Speed Indicator)
        centre = (C.WN_W//2+300, C.WN_H*0.85)
        rect = self.images.speed_dial.get_rect(center=centre)
        hud_surface.blit(self.images.speed_dial, rect)

        speed_knots = self.plane.vel.length() * 1.94384  # Convert to knots
        angle = 90 - min(336, 270 * speed_knots/160)
        draw_text(hud_surface, (C.WN_W//2+300, C.WN_H*0.85 - 20), 'centre', 'centre', f"{int(self.plane.vel.length() * 1.94384):03d}", (192, 192, 192), 25, self.font)
        draw_needle(hud_surface, centre, angle, 100)

        # Altimeter (left)
        alt_centre = (C.WN_W//2 - 110, int(C.WN_H*0.74))
        alt_size = 160, 70
        alt_rect = pg.Rect(0, 0, *alt_size)
        alt_rect.center = alt_centre
        pg.draw.rect(hud_surface, (255, 255, 255), alt_rect)
        inner_alt_rect = pg.Rect(0, 0, alt_size[0]-4, alt_size[1]-4)
        inner_alt_rect.center = alt_centre
        pg.draw.rect(hud_surface, (0, 0, 0), inner_alt_rect)
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
        text_colour: Colour = BLUE if vs_ft_per_min > 0 else WHITE if vs_ft_per_min == 0 else BROWN
        draw_text(
            hud_surface,
            vsi_centre,
            'centre', 'centre',
            f"{vs_ft_per_min:+,.0f} / min",
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
        pg.draw.rect(hud_surface, (0, 0, 0), inner_loc_rect)

        draw_text(
            hud_surface,
            loc_centre,
            'centre', 'centre',
            f"({self.plane.pos.x:,.0f}m, {self.plane.pos.z:,.0f}m)",
            (255, 255, 255),
            22,
            self.fonts.monospaced
        )

        # Throttle bar
        draw_text(hud_surface, (C.WN_W*0.86, C.WN_H*0.97), 'centre', 'centre', "Throttle", (25, 20, 18), 30, self.fonts.monospaced)
        pg.draw.line(hud_surface, (51, 43, 37), (C.WN_W*0.86, C.WN_H*0.94), (C.WN_W*0.86, C.WN_H*0.75), 3)
        size = 40, 20
        rect = pg.Rect(0, 0, *size)
        rect.center = (C.WN_W*0.86, C.WN_H*0.94 - C.WN_H*0.19*(self.plane.throttle_frac))  # type: ignore
        pg.draw.rect(hud_surface, (255, 255, 255), rect)

        # Stall warning
        draw_text(hud_surface, (C.WN_W//2-160, C.WN_H*0.92), 'centre', 'centre', "STALL", (25, 20, 18), 20, self.fonts.monospaced)
        warning_col = (255, 0, 0) if self.show_stall_warning else (0, 0, 0)
        pg.draw.circle(hud_surface, (51, 43, 37), (C.WN_W//2-160, C.WN_H*0.96), 12)
        pg.draw.circle(hud_surface, (warning_col), (C.WN_W//2-160, C.WN_H*0.96), 10)
        if self.show_stall_warning:
            draw_text(hud_surface, (C.WN_W//2, C.WN_H*0.62), 'centre', 'centre', "STALL", (210, 0, 0), 50, self.fonts.monospaced)

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
            DARK_BLUE,
            (0, 0, inner_ai_rect.width, horizon_y)
        )

        # Ground (below horizon)
        pg.draw.rect(
            ai_surface,
            DARK_BROWN,
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
                    WHITE,
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
                ai_surface, WHITE,
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
                ai_surface, WHITE,
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
        colour_scheme = SKY_COLOUR_SCHEMES[self.time_of_day]

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
        gl.glTranslatef(-self.plane.pos.x, -(self.plane.pos.y+C.CAMERA_OFFSET_Y), -self.plane.pos.z)

        self.ground.draw()
        self.draw_hud()
