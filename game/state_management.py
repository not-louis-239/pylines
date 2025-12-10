import pygame as pg
from core.constants import ScancodeWrapper, Surface
from core.asset_manager import load_images

class Game:
    def __init__(self) -> None:
        self.images = load_images()
        self.states: dict[str, State] = {
            "title": TitleScreen(self),
            "game": GameScreen(self),
        }
        self.state = self.states["title"]

    def update(self) -> None:
        self.state.update()

    def take_input(self, keys: ScancodeWrapper, dt: int) -> None:
        self.state.take_input(keys, dt)

    def draw(self, wn: Surface) -> None:
        self.state.draw(wn)

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

class GameScreen(State):
    def __init__(self, game: Game) -> None:
        super().__init__(game)

    def draw(self, wn: Surface):
        # TODO: Sky gradient
        pass