from __future__ import annotations
from typing import TYPE_CHECKING

import pygame as pg
from core.utils import frange
from core.colours import SKY_COLOUR_SCHEMES, interpolate_cols
import core.constants as C
from game.state_management import State
from objects.objects import Plane

if TYPE_CHECKING:
    from core.custom_types import Surface
    from game.game import Game

class GameScreen(State):
    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.plane = Plane()
        self.time_of_day = "night"

    def draw(self, wn: Surface):
        colour_scheme = SKY_COLOUR_SCHEMES[self.time_of_day]
        wn.fill(colour_scheme.high)

        GRADIENT_STEPS = 75
        GRADIENT_SEG_HEIGHT = C.WN_H//(2*GRADIENT_STEPS)+1
        for i in range(GRADIENT_STEPS):
            y = i * (C.WN_H / 2) / GRADIENT_STEPS
            t = i / (GRADIENT_STEPS)
            interpolated_col = interpolate_cols(colour_scheme.high, colour_scheme.mid, t)
            pg.draw.rect(wn, interpolated_col, (0, y, C.WN_W, GRADIENT_SEG_HEIGHT))
        for i in range(GRADIENT_STEPS):
            y = (C.WN_H / 2) + i * (C.WN_H / 2) / GRADIENT_STEPS
            t = i / (GRADIENT_STEPS)
            interpolated_col = interpolate_cols(colour_scheme.mid, colour_scheme.low, t)
            pg.draw.rect(wn, interpolated_col, (0, y, C.WN_W, GRADIENT_SEG_HEIGHT))
