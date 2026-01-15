# Copyright 2025-2026 Louis Masarei-Boulton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

import pygame as pg

from pylines.core.asset_manager import Assets, MapData
from pylines.core.data_manager import load_data, save_data
from pylines.core.heightmap import Heightmap
from pylines.game.screens.game_screen import GameScreen
from pylines.game.screens.settings import SettingsScreen
from pylines.game.screens.title import TitleScreen

if TYPE_CHECKING:
    from pylines.core.custom_types import EventList, ScancodeWrapper, Surface
    from pylines.game.states import State

class Game:
    class States(Enum):
        TITLE = auto()
        GAME = auto()
        SETTINGS = auto()

    def __init__(self) -> None:
        # Load assets and files
        self.assets = Assets()
        self.save_data, *_ = load_data("data/save_data.json")

        # Set up keys and states
        self.prev_keys: ScancodeWrapper = pg.key.get_pressed()

        # The MapData instance should be garbage collected
        # after Game has derived its height, size and data
        map_data: MapData = self.assets.map
        self.heightmap: Heightmap = Heightmap(
            map_data,
            diagonal_split='AD'
        )
        self.states: dict[Game.States, State] = {
            Game.States.TITLE: TitleScreen(self),
            Game.States.GAME: GameScreen(self),
            Game.States.SETTINGS: SettingsScreen(self),
        }

        # Music
        self.music_channel = pg.mixer.Channel(0)

        # States
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

    def quit_game(self):
        save_data(self.save_data)
