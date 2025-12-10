from __future__ import annotations

from core.custom_types import ScancodeWrapper, Surface

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game.game import Game

class State:
    def __init__(self, game: Game) -> None:
        self.game = game

    def update(self) -> None:
        pass

    def take_input(self, keys: ScancodeWrapper, dt: int) -> None:
        pass

    def draw(self, wn: Surface):
        pass

class TitleScreen(State):
    def __init__(self, game: Game):
        super().__init__(game)

    def draw(self, wn: Surface):
        wn.fill((50, 50, 50))
