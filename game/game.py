from __future__ import annotations
from typing import TYPE_CHECKING
from core.asset_manager import Assets
from game.state_management import TitleScreen
from game.game_screen import GameScreen

if TYPE_CHECKING:
    from core.custom_types import ScancodeWrapper, Surface
    from game.state_management import State


class Game:
    def __init__(self) -> None:
        self.assets = Assets()
        self.states: dict[str, State] = {
            "title": TitleScreen(self),
            "game": GameScreen(self),
        }
        self.state = "game"

    def update(self) -> None:
        self.states[self.state].update()

    def take_input(self, keys: ScancodeWrapper, dt: int) -> None:
        self.states[self.state].take_input(keys, dt)

    def draw(self, wn: Surface) -> None:
        self.states[self.state].draw(wn)
