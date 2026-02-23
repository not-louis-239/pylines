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

from typing import TYPE_CHECKING

import pygame as pg

from pylines.core.paths import DIRECTORIES
from pylines.core.asset_manager import Assets
from pylines.core.asset_manager_helpers import MusicID
from pylines.core.audio_manager import SFXChannelID
from pylines.core.data_manager import ConfigObject, load_data, save_data
from pylines.game.environment import Environment
from pylines.game.live_config_presets import LiveConfigPresets
from pylines.game.screens.briefing import BriefingScreen
from pylines.game.screens.loading_screen import LoadingScreen
from pylines.game.screens.settings import SettingsScreen
from pylines.game.screens.credits import CreditsScreen
from pylines.game.screens.title import TitleScreen
from pylines.game.states import State, StateID
from pylines.game.managers.menu_images_manager import MenuImageManager
from pylines.game.managers.smoke_manager import SmokeManager
from pylines.core.audio_manager import AudioManager

if TYPE_CHECKING:
    from pylines.core.custom_types import EventList, ScancodeWrapper, Surface

class Game:
    def __init__(self) -> None:
        # Lazy-load structure / lightweight constructor

        self.assets = Assets()
        self.audio_manager = AudioManager(self)

        self.menu_image_manager = MenuImageManager(self.assets.images.menu_images)  # This is in Game to make it accessible from multiple states
        self.smoke_manager = SmokeManager(self.assets.images)

        self.save_data: ConfigObject
        self.save_data, *_ = load_data(DIRECTORIES.data / "save_data.json")

        config_presets_raw = self.assets.config_presets
        self.config_presets = LiveConfigPresets(config_presets_raw, self.assets.images)

        self.prev_keys: ScancodeWrapper = pg.key.get_pressed()
        self.env: Environment | None = None

        self.states: dict[StateID, State] = {
            StateID.LOADING: LoadingScreen(self),
            StateID.TITLE: TitleScreen(self),
            StateID.SETTINGS: SettingsScreen(self),
            StateID.BRIEFING: BriefingScreen(self),
            StateID.CREDITS: CreditsScreen(self)
        }

        self.state: StateID = StateID.LOADING
        self.enter_state(StateID.LOADING)

    def enter_state(self, state_name: StateID):
        assert self.assets is not None
        assert self.states is not None

        prev_state, self.state = self.state, state_name
        self.audio_manager.on_state_change(prev_state, self.state)
        self.states[state_name].enter_state()

    def update(self, dt) -> None:
        assert self.states is not None

        self.states[self.state].update(dt)

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        assert self.states is not None

        self.states[self.state].take_input(keys, events, dt)

    def draw(self, wn: Surface) -> None:
        assert self.states is not None

        self.states[self.state].draw(wn)

    def quit_game(self):
        save_data(self.save_data)
