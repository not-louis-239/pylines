import pygame as pg
from typing import TypeAlias

# Type aliases
Colour: TypeAlias = tuple[int, int, int]
RealNumber: TypeAlias = int | float
Surface: TypeAlias = pg.Surface
ScancodeWrapper: TypeAlias = pg.key.ScancodeWrapper

# Constants
FPS = 60
TPS = 60
WN_W = 1000
WN_H = 750

# Colours
WHITE = (255, 255, 255)