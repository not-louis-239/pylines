from __future__ import annotations
from typing import TYPE_CHECKING
import math

import pygame as pg
from core.colours import SKY_COLOUR_SCHEMES
import core.constants as C
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
        self.ground = Ground()
        self.sky = Sky()
        self.time_of_day = "night"

        # Camera settings for testing
        self.camera_pos = pg.Vector3(0, 5, 10)
        self.camera_rot = pg.Vector3(0, 0, 0)  # Pitch, Yaw, Roll

        # Font for text rendering
        self.font = pg.font.Font(self.fonts.monospaced, 36)

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

    def draw_text(self, x: int, y: int, text: str):
        text_surface = self.font.render(text, True, (255, 255, 255, 255))
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

        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)  # type: ignore

        # Draw sky gradient background
        self.sky.draw(colour_scheme)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        # Apply camera transformations
        gl.glRotatef(self.camera_rot.x, 1, 0, 0) # Pitch
        gl.glRotatef(self.camera_rot.y, 0, 1, 0) # Yaw
        gl.glRotatef(self.camera_rot.z, 0, 0, 1) # Roll
        gl.glTranslatef(-self.camera_pos.x, -self.camera_pos.y, -self.camera_pos.z)

        self.ground.draw()

        # Draw text overlay
        gl.glColor3f(1, 1, 1)
        pos_text = f"Pos: ({self.camera_pos.x:.2f}, {self.camera_pos.y:.2f}, {self.camera_pos.z:.2f})"
        rot_text = f"Rot: ({self.camera_rot.x:.2f}, {self.camera_rot.y:.2f}, {self.camera_rot.z:.2f})"
        self.draw_text(10, 10, pos_text)
        self.draw_text(10, 50, rot_text)

