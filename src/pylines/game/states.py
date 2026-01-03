"""Generic state management module that defines state types"""

from __future__ import annotations
from typing import TYPE_CHECKING

from pylines.core.custom_types import ScancodeWrapper, Surface, EventList

if TYPE_CHECKING:
    from pylines.game.game import Game

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
