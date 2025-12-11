from __future__ import annotations
from typing import TYPE_CHECKING
import math

import pygame as pg
from core.utils import frange
from core.colours import SKY_COLOUR_SCHEMES, interpolate_cols
import core.constants as C
from game.state_management import State
from objects.objects import Plane, Ground # Import Ground
from OpenGL.GL import *   # type: ignore
from OpenGL.GLU import *  # type: ignore

if TYPE_CHECKING:
    from core.custom_types import Surface, ScancodeWrapper
    from game.game import Game

class GameScreen(State):
    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.plane = Plane()
        self.ground = Ground()
        self.time_of_day = "night"

        # Camera settings for testing
        self.camera_pos = pg.Vector3(0, 5, 10)
        self.camera_rot = pg.Vector3(0, 0, 0) # Pitch, Yaw, Roll

        # Font for text rendering
        self.font = pg.font.Font(None, 36)

    def take_input(self, keys: ScancodeWrapper, dt: int) -> None:
        speed = 0.01 * dt
        rot_speed = 0.05 * dt

        # Movement
        if keys[pg.K_w]: # Forward
            self.camera_pos.x -= speed * math.sin(math.radians(self.camera_rot.y))
            self.camera_pos.z -= speed * math.cos(math.radians(self.camera_rot.y))
        if keys[pg.K_s]: # Backward
            self.camera_pos.x += speed * math.sin(math.radians(self.camera_rot.y))
            self.camera_pos.z += speed * math.cos(math.radians(self.camera_rot.y))
        if keys[pg.K_a]: # Strafe Left
            self.camera_pos.x -= speed * math.cos(math.radians(self.camera_rot.y))
            self.camera_pos.z += speed * math.sin(math.radians(self.camera_rot.y))
        if keys[pg.K_d]: # Strafe Right
            self.camera_pos.x += speed * math.cos(math.radians(self.camera_rot.y))
            self.camera_pos.z -= speed * math.sin(math.radians(self.camera_rot.y))
        if keys[pg.K_r]: # Up
            self.camera_pos.y += speed
        if keys[pg.K_f]: # Down
            self.camera_pos.y -= speed

        # Rotation
        if keys[pg.K_UP]:
            self.camera_rot.x -= rot_speed
        if keys[pg.K_DOWN]:
            self.camera_rot.x += rot_speed
        if keys[pg.K_LEFT]:
            self.camera_rot.y -= rot_speed
        if keys[pg.K_RIGHT]:
            self.camera_rot.y += rot_speed
        if keys[pg.K_q]:
            self.camera_rot.z -= rot_speed
        if keys[pg.K_e]:
            self.camera_rot.z += rot_speed

    def _draw_text(self, x: int, y: int, text: str):
        text_surface = self.font.render(text, True, (255, 255, 255, 255), (0, 0, 0, 0))
        text_data = pg.image.tostring(text_surface, "RGBA", True)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, C.WN_W, C.WN_H, 0)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_surface.get_width(), text_surface.get_height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x, y)
        glTexCoord2f(1, 0); glVertex2f(x + text_surface.get_width(), y)
        glTexCoord2f(1, 1); glVertex2f(x + text_surface.get_width(), y + text_surface.get_height())
        glTexCoord2f(0, 1); glVertex2f(x, y + text_surface.get_height())
        glEnd()

        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glDeleteTextures(1, [texid])

        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    def draw(self, wn: Surface):
        colour_scheme = SKY_COLOUR_SCHEMES[self.time_of_day]

        # Clear the screen with the specified background color (normalized to 0.0-1.0)
        glClearColor(colour_scheme.high[0]/255.0, colour_scheme.high[1]/255.0, colour_scheme.high[2]/255.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # type: ignore

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Apply camera transformations
        glRotatef(self.camera_rot.x, 1, 0, 0) # Pitch
        glRotatef(self.camera_rot.y, 0, 1, 0) # Yaw
        glRotatef(self.camera_rot.z, 0, 0, 1) # Roll
        glTranslatef(-self.camera_pos.x, -self.camera_pos.y, -self.camera_pos.z)

        self.ground.draw()

        # Draw text overlay
        pos_text = f"Pos: ({self.camera_pos.x:.2f}, {self.camera_pos.y:.2f}, {self.camera_pos.z:.2f})"
        rot_text = f"Rot: ({self.camera_rot.x:.2f}, {self.camera_rot.y:.2f}, {self.camera_rot.z:.2f})"
        self._draw_text(10, 10, pos_text)
        self._draw_text(10, 50, rot_text)


