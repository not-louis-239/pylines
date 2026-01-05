from typing import cast, TYPE_CHECKING, Any, Callable, Literal
from dataclasses import dataclass

import pygame as pg
import OpenGL.GL as gl
import OpenGL.GLU as glu

import pylines.core.constants as C
from pylines.core.custom_types import ScancodeWrapper, EventList, Surface
from pylines.core.utils import draw_text
from pylines.game.states import State
from pylines.objects.buttons import Button

if TYPE_CHECKING:
    from pylines.game.game import Game

@dataclass(frozen=True)
class ConfigEntry:
    label: str
    get: Callable[[], Any]
    set: Callable[[Any], None]
    kind: type

class SettingsScreen(State):
    def __init__(self, game: Game):
        super().__init__(game)
        self.display_surface = pg.Surface((C.WN_W, C.WN_H), pg.SRCALPHA)
        self.texture_id = gl.glGenTextures(1)
        self.back_button = Button(
            (170, C.WN_H-90), 300, 80, (25, 75, 75), (200, 255, 255),
            "Back to Main Menu", self.fonts.monospaced, 30
        )

        data = self.game.save_data
        self.toggle_ops: list[ConfigEntry] = [
            ConfigEntry(
                "Time Option",
                lambda: data.time_option,
                lambda val: setattr(data, "time_option", val),
                str
            )
        ]
        self.toggle_idx = 0

    def reset(self) -> None:
        pass

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        if self.back_button.check_click(events):
            self.game.enter_state(self.game.States.TITLE)

        if self.pressed(keys, pg.K_UP):
            self.toggle_idx -= 1
            self.toggle_idx %= len(self.toggle_ops)
        if self.pressed(keys, pg.K_DOWN):
            self.toggle_idx += 1
            self.toggle_idx %= len(self.toggle_ops)

        self.update_prev_keys(keys)

    def draw(self, wn: Surface):
        # Fill the display surface
        self.display_surface.fill((0, 0, 0))

        # Draw text
        draw_text(self.display_surface, (C.WN_W//2, C.WN_H*0.15), 'centre', 'centre', "Settings", (0, 192, 255), 40, self.fonts.monospaced)
        draw_text(self.display_surface, (C.WN_W//2, C.WN_H*0.8), 'centre', 'centre', "This screen is under construction.", (255, 192, 0), 30, self.fonts.monospaced)
        self.back_button.draw(self.display_surface)

        data = self.game.save_data
        drawn_ops = {
            "Time Option": data.time_option,
            "Custom Time": data.time_custom,
            "Invert Y-Axis": data.invert_y_axis
        }

        for i, (ui_str, option) in enumerate(drawn_ops.items()):
            TEXT_COLOUR = (192, 230, 255) if i == self.toggle_idx else (255, 255, 255)
            VAL_COLOUR = (170, 210, 255) if i == self.toggle_idx else (220, 220, 220)

            draw_text(self.display_surface, (C.WN_W*0.35, C.WN_H * (0.4+0.08*i)), 'left', 'centre', ui_str, TEXT_COLOUR, 30, self.fonts.monospaced)
            draw_text(self.display_surface, (C.WN_W*0.65, C.WN_H * (0.4+0.08*i)), 'right', 'centre', str(option), VAL_COLOUR, 30, self.fonts.monospaced)

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