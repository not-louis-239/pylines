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

import pathlib
from typing import TypeAlias

import pygame as pg

# Visual types
Colour: TypeAlias = tuple[int, int, int]
AColour: TypeAlias = tuple[int, int, int, int]

# Mathematical types
RealNumber: TypeAlias = int | float
Coord2: TypeAlias = tuple[RealNumber, RealNumber]
Coord3: TypeAlias = tuple[RealNumber, RealNumber, RealNumber]

# Event types
ScancodeWrapper: TypeAlias = pg.key.ScancodeWrapper
EventList: TypeAlias = list[pg.event.Event]

# Asset types
Surface: TypeAlias = pg.Surface
Sound: TypeAlias = pg.mixer.Sound
Path: TypeAlias = pathlib.Path
Font: TypeAlias = pg.font.Font

# Config
ConfigValue: TypeAlias = int | bool   # more will be added when needed