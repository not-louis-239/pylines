from __future__ import annotations
from typing import TYPE_CHECKING, cast

import pygame as pg
from core.colours import SKY_COLOUR_SCHEMES
from core.custom_types import RealNumber, AColour
import core.constants as C
from core.utils import clamp
from game.state_management import State
from objects.objects import Plane, Ground, Sky
import OpenGL.GL as gl
import OpenGL.GLU as glu

if TYPE_CHECKING:
    from core.custom_types import Surface, ScancodeWrapper
    from game.game import Game

class GameScreen(State):
    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.plane = Plane()
        self.ground = Ground(game.assets.images.test_grass) # Pass the loaded image to Ground
        self.sky = Sky()
        self.time_of_day: str = "sunset"
        self.show_stall_warning: bool = False

        # Font for text rendering
        self.font = pg.font.Font(game.assets.fonts.monospaced, 36)

    def update(self, dt: int):
        self.plane.update(dt)

        self.show_stall_warning = self.plane.rot.x < -self.plane.model.stall_angle

    def take_input(self, keys: ScancodeWrapper, dt: int) -> None:
        rot_speed = 50 * dt/1000
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
        self.plane.rot.y %=360
        self.plane.rot.z %= 360
        self.plane.rot.x = clamp(self.plane.rot.x, -90, 90)

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

        # --- HUD ---
        # Disable depth testing to draw HUD on top of 3D scene
        gl.glDisable(gl.GL_DEPTH_TEST)

        gl.glColor3f(1, 1, 1) # Set color for text

        # Position and Rotation
        altitude_in_ft = self.plane.pos.y * 3.28084  # Convert to ft

        altitude_text = f"Altitude: {altitude_in_ft:,.0f} ft"

        pitch_text = f"Pitch: {-self.plane.rot.x:,.0f}°"
        dir_text = f"Dir: {self.plane.rot.y:,.0f}°"
        roll_text = f"Roll: {(self.plane.rot.z+180)%360-180:,.0f}°"

        loc_text = f"Loc: ({self.plane.pos.x:,.0f}, {self.plane.pos.z:,.0f})"

        self.draw_text(C.WN_W//2-100, C.WN_H*0.20, pitch_text)
        self.draw_text(C.WN_W//2-100, C.WN_H*0.25, dir_text)
        self.draw_text(C.WN_W//2-100, C.WN_H*0.30, roll_text)

        self.draw_text(C.WN_W//2-100, C.WN_H*0.75, loc_text)
        self.draw_text(C.WN_W//2-100, C.WN_H*0.8, altitude_text)

        # Throttle
        if self.plane.throttle_frac >= 1:
            throttle_text = "Full"
        elif self.plane.throttle_frac > 0:
            throttle_text = f"{self.plane.throttle_frac:.0%}"
        else:
            throttle_text = "None"
        self.draw_text(30, C.WN_H - 100, f"Throttle: {throttle_text}")

        if self.show_stall_warning:
            gl.glColor3f(1, 0, 0) # Set color for text
            self.draw_text(C.WN_W//2-20, C.WN_H-100, "[STALL]")

        # Re-enable depth testing for the next frame
        gl.glEnable(gl.GL_DEPTH_TEST)

