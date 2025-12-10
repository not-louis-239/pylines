from typing import TypeAlias
import pygame as pg

# Visual types
Colour: TypeAlias = tuple[int, int, int]
AColour: TypeAlias = tuple[int, int, int, int]

# Mathematical types
RealNumber: TypeAlias = int | float
Coord3: TypeAlias = tuple[RealNumber, RealNumber, RealNumber]

# Pygame types
ScancodeWrapper: TypeAlias = pg.key.ScancodeWrapper
Surface: TypeAlias = pg.Surface
Sound: TypeAlias = pg.mixer.Sound

