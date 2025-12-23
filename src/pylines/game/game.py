from __future__ import annotations

from typing import TYPE_CHECKING

import pygame as pg

from pylines.core.asset_manager import Assets
from pylines.game.game_screen import GameScreen
from pylines.game.state_management import TitleScreen, SettingsScreen

if TYPE_CHECKING:
    from pylines.core.custom_types import ScancodeWrapper, Surface
    from pylines.game.state_management import State


class Game:
    def __init__(self) -> None:
        self.assets = Assets()
        self.prev_keys: ScancodeWrapper = pg.key.get_pressed()
        self.states: dict[str, State] = {
            "title": TitleScreen(self),
            "game": GameScreen(self),
            "settings": SettingsScreen(self),
        }
        self.enter_state('title')

    def enter_state(self, state_name: str):
        self.state = state_name
        self.states[state_name].enter_state()

    def update(self, dt) -> None:
        self.states[self.state].update(dt)

    def take_input(self, keys: ScancodeWrapper, events: list[pg.event.Event], dt: int) -> None:
        self.states[self.state].take_input(keys, events, dt)

    def draw(self, wn: Surface) -> None:
        self.states[self.state].draw(wn)
