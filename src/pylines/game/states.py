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

"""Generic state management module that defines state types"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

from pylines.core.custom_types import EventList, ScancodeWrapper, Surface

if TYPE_CHECKING:
    from pylines.game.game import Game

class StateID(Enum):
    TITLE = auto()
    GAME = auto()
    SETTINGS = auto()
    LOADING = auto()
    BRIEFING = auto()

class State:
    def __init__(self, game: Game) -> None:
        self.game = game
        self.images = game.assets.images
        self.fonts = game.assets.fonts
        self.sounds = game.assets.sounds

    def reset(self) -> None:
        raise NotImplementedError

    def enter_state(self) -> None:
        self.reset()

    def update(self, dt: int) -> None:
        pass

    def update_prev_keys(self, keys: ScancodeWrapper):
        self.game.prev_keys = keys

    def pressed(self, keys: ScancodeWrapper, key: int) -> bool:
        """Returns True if a key is pressed now but not last frame."""
        return keys[key] and not self.game.prev_keys[key]

    def take_input(self, keys: ScancodeWrapper, events: EventList, dt: int) -> None:
        pass

    def draw(self, wn: Surface):
        pass
