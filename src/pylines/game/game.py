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

        self.music_channel = pg.mixer.Channel(0)  # Reserve channel 0 for music                                                    │
        self.state: Game.States = Game.States.TITLE  # Explicitly set initial state
        self.enter_state(Game.States.TITLE)

    def enter_state(self, state_name: States):
        prev_state = self.state
        self.state = state_name

        menu_states = (self.States.TITLE, self.States.SETTINGS)
        was_in_menu = prev_state in menu_states
        is_entering_menu = state_name in menu_states
        # Fade out music if leaving a menu state for a non-menu state
        if was_in_menu and not is_entering_menu:
            self.music_channel.fadeout(1500)
        # Play music if entering a menu state from a non-menu state or if transitioning between menu states and music is not playing                                                                                                                          │
        elif is_entering_menu and (not was_in_menu or not self.music_channel.get_busy()):
            self.music_channel.play(self.assets.sounds.menu_music, loops=-1)

        self.states[state_name].enter_state()

    def update(self, dt) -> None:
        self.states[self.state].update(dt)

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        self.states[self.state].take_input(keys, events, dt)

    def draw(self, wn: Surface) -> None:
        self.states[self.state].draw(wn)
