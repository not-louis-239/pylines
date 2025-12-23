from __future__ import annotations

from typing import TYPE_CHECKING
from enum import Enum, auto

import pygame as pg

from pylines.core.asset_manager import Assets
from pylines.game.game_screen import GameScreen
from pylines.game.state_management import TitleScreen, SettingsScreen

if TYPE_CHECKING:
    from pylines.core.custom_types import ScancodeWrapper, Surface, EventList
    from pylines.game.state_management import State

class Game:
    class States(Enum):
        TITLE = auto()
        GAME = auto()
        SETTINGS = auto()

    def __init__(self) -> None:
        self.assets = Assets()
        self.prev_keys: ScancodeWrapper = pg.key.get_pressed()
        self.states: dict[Game.States, State] = {
            Game.States.TITLE: TitleScreen(self),
            Game.States.GAME: GameScreen(self),
            Game.States.SETTINGS: SettingsScreen(self),
        }
        self.enter_state(Game.States.TITLE)

    def enter_state(self, state_name: States):
        self.state = state_name
        self.states[state_name].enter_state()

    def update(self, dt) -> None:
        self.states[self.state].update(dt)

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        self.states[self.state].take_input(keys, events, dt)

    def draw(self, wn: Surface) -> None:
        self.states[self.state].draw(wn)
