from typing import TypeAlias
import pathlib
import pygame as pg

# Visual types
Colour: TypeAlias = tuple[int, int, int]
AColour: TypeAlias = tuple[int, int, int, int]

# Mathematical types
RealNumber: TypeAlias = int | float
Coord3: TypeAlias = tuple[RealNumber, RealNumber, RealNumber]

# Event types
ScancodeWrapper: TypeAlias = pg.key.ScancodeWrapper

# Asset types
Surface: TypeAlias = pg.Surface
Sound: TypeAlias = pg.mixer.Sound
Path: TypeAlias = pathlib.Path
Font: TypeAlias = pg.font.Font