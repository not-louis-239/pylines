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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pylines.core.custom_types import Surface

if TYPE_CHECKING:
    from pylines.core.custom_types import Surface
    from pylines.game.game import Game

if TYPE_CHECKING:
    from pylines.game.game import Game

@dataclass
class PopupMenuState:
    visible: bool = False
    animation_open: float = 0  # 0 = down, 1 = up

class PopupMenu(ABC):
    def __init__(self, game: Game) -> None:
        self.state = PopupMenuState()
        self.game = game

    @abstractmethod
    def draw(self, surface: Surface) -> None:
        raise NotImplementedError

    def toggle_visibility(self) -> None:
        self.state.visible = not self.state.visible