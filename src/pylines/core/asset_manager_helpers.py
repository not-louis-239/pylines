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

import numpy as np
from numpy.typing import NDArray
import pygame as pg

from abc import ABC
from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from pathlib import Path

class FLine:
    """Formatted line for help text"""

    class Style(Enum):
        NORMAL = auto()
        HEADING_1 = auto()
        HEADING_2 = auto()
        BULLET = auto()

    def __init__(self, text: str, indent: int, style: Style = Style.NORMAL):
        self.text = text
        self.indent = indent
        self.style = style

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"text={self.text!r}, "
            f"indent={self.indent}, "
            f"style={self.style}"
            f")"
        )

@dataclass
class CreditLine:
    name: str
    role: str
    license: str

@dataclass
class Notes:
    upper: str
    main: str
    lower: str

@dataclass
class CreditEntry(ABC): pass

@dataclass
class CreditEntryCompact(CreditEntry):
    lines: list[CreditLine]

@dataclass
class CreditEntryNotes(CreditEntry):
    info: Notes

@dataclass
class CreditEntryCompactNotes(CreditEntry):
    lines: list[str]

@dataclass
class CreditSection:
    heading: str
    entries: list[CreditEntry]

@dataclass
class CreditsContainer:
    """Class designated to storing credits data"""

    version: str
    sections: list[CreditSection]
    notes: list[str]

class ControlsSectionID(StrEnum):
    # This differentiates individual sections to allow
    # custom rendering behaviour for each controls section
    MAIN = "Main Controls"
    DISPLAYS = "Displays"
    MAP = "Map Manipulation"
    UTILITIES = "Utilities"
    JUKEBOX = "Jukebox"

@dataclass
class ControlsSection:
    keys: dict[str, str]  # key, action
    note: str | None      # None = no note

class MusicID(StrEnum):
    OPEN_TWILIGHT = "Open Twilight"
    NIGHTGLIDE = "Nightglide"
    SKYLIGHT = "Skylight"

@dataclass
class JukeboxTrack:
    name: str
    path: Path

    def __post_init__(self):
        """Dynamically compute a sound object based on the track's path"""

        self.sound_obj: pg.mixer.Sound = pg.mixer.Sound(str(self.path))
        self.sound_arr: NDArray[np.int16] = pg.sndarray.array(self.sound_obj)
