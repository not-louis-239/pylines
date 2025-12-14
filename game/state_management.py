from __future__ import annotations

from core.custom_types import ScancodeWrapper, Surface
import pygame as pg
import OpenGL.GL as gl
import OpenGL.GLU as glu
import core.constants as C
from core.utils import draw_text
from typing import cast

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game.game import Game

class State:
    def __init__(self, game: Game) -> None:
        self.game = game
        self.images = game.assets.images
        self.fonts = game.assets.fonts
        self.sounds = game.assets.sounds

    def reset(self) -> None:
        raise NotImplementedError

    def enter_state(self) -> None:
        self.reset()

    def update(self, dt: int) -> None:
        pass

    def update_prev_keys(self, keys: ScancodeWrapper):
        self.game.prev_keys = keys

    def take_input(self, keys: ScancodeWrapper, dt: int) -> None:
        pass

    def draw(self, wn: Surface):
        pass

class TitleScreen(State):
    def __init__(self, game: Game):
        super().__init__(game)
        self.fill = False
        self.display_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
        self.texture_id = gl.glGenTextures(1)

    def reset(self) -> None:
        self.sounds.menu_music.play(-1)
        self.sounds.stall_warning.stop()

    def take_input(self, keys: ScancodeWrapper, dt: int) -> None:
        def pressed(key: int) -> bool:
            """Returns True if a key is pressed now but not last frame."""
            return keys[key] and not self.game.prev_keys[key]

        if pressed(pg.K_SPACE):
            self.game.enter_state('game')

        self.update_prev_keys(keys)

    def draw(self, wn: Surface):
        # Fill the display surface
        self.display_surface.fill((255, 255, 255) if self.fill else (0, 0, 0))
        rect = self.images.logo.get_rect(center=(C.WN_W//2, C.WN_H*0.25))
        self.display_surface.blit(self.images.logo, rect)
        draw_text(self.display_surface, (C.WN_W//2, 3*C.WN_H//5), 'centre', 'centre', "Press Space to begin.", (255, 255, 255), 30, self.fonts.monospaced)

        # Convert the Pygame surface to an OpenGL texture
        texture_data = pg.image.tostring(self.display_surface, 'RGBA', True)

        gl.glClear(cast(int, gl.GL_COLOR_BUFFER_BIT) | cast(int, gl.GL_DEPTH_BUFFER_BIT))
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, C.WN_W, C.WN_H, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, texture_data)

        # Set up the projection and modelview matrices for 2D drawing
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        glu.gluOrtho2D(0, C.WN_W, 0, C.WN_H)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()

        gl.glDisable(gl.GL_DEPTH_TEST)
        # Draw a full-screen quad with the texture
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBegin(gl.GL_QUADS)
        gl.glTexCoord2f(0, 0)
        gl.glVertex2f(0, 0)
        gl.glTexCoord2f(1, 0)
        gl.glVertex2f(C.WN_W, 0)
        gl.glTexCoord2f(1, 1)
        gl.glVertex2f(C.WN_W, C.WN_H)
        gl.glTexCoord2f(0, 1)
        gl.glVertex2f(0, C.WN_H)
        gl.glEnd()
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_DEPTH_TEST)

        # Restore the previous projection and modelview matrices
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPopMatrix()
