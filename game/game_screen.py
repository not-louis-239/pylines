from __future__ import annotations
from typing import TYPE_CHECKING

import pygame as pg
from core.utils import frange
from core.colours import SKY_COLOUR_SCHEMES, interpolate_cols
import core.constants as C
from game.state_management import State
from objects.objects import Plane, Ground # Import Ground
from OpenGL.GL import *   # type: ignore
from OpenGL.GLU import *  # type: ignore

if TYPE_CHECKING:
    from core.custom_types import Surface
    from game.game import Game

class GameScreen(State):
    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.plane = Plane()
        self.ground = Ground() # Instantiate Ground
        self.time_of_day = "night"

    def draw(self, wn: Surface):
        colour_scheme = SKY_COLOUR_SCHEMES[self.time_of_day]

        # Clear the screen with the specified background color (normalized to 0.0-1.0)
        glClearColor(colour_scheme.high[0]/255, colour_scheme.high[1]/255, colour_scheme.high[2]/255, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # type: ignore

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Basic camera setup: gluLookAt(eyeX, eyeY, eyeZ, centerX, centerY, centerZ, upX, upY, upZ)
        gluLookAt(0, 5, 0,  # Camera position
                  0, 0, 0,   # Look-at point
                  0, 1, 0)   # Up vector

        self.ground.draw() # Draw the ground


