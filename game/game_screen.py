from __future__ import annotations
from typing import TYPE_CHECKING
from core.colours import SKY_COLOUR_SCHEMES
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
        wn.fill(SKY_COLOUR_SCHEMES[self.time_of_day].high)
        for y in range(0):
            ...
