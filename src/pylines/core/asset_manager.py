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

"""
asset_manager.py

    This module is reserved for asset loading only. All structures in
    this module should be purely to load and store assets. They should
    not be involved in computations or logic beyond asset file management.
"""

import json
from enum import Enum, auto
from pathlib import Path
from typing import cast

import numpy as np
import pygame as pg
from PIL import Image
from pygame.transform import scale, scale_by

import pylines.core.paths as paths
from pylines.core.custom_types import Sound, Surface


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

class AssetBank:
    """Base class to store assets. Objects of this type should be
    purely used for asset loading and should not contain any logic."""

    def __init__(self) -> None:
        """Base method to set assets."""
        self.augment()

    def augment(self) -> None:
        """Base method to adjust assets."""
        pass

    def _load(self) -> None:
        """Base method to load individual assets."""
        raise NotImplementedError

class Fonts(AssetBank):
    def __init__(self) -> None:
        p = "Inconsolata-VariableFont_wdth,wght.ttf"
        self.monospaced: Path = self._load(p)
        self.augment()

    def _load(self, name: str) -> Path:
        return paths.FONTS_DIR / name

class Images(AssetBank):
    def __init__(self):
        self.snow = self._load("snow.png")
        self.alpine_rock = self._load("alpine_rock.png")
        self.treeline_rock = self._load("treeline_rock.png")
        self.high_grass = self._load("high_grass.png")
        self.low_grass = self._load("low_grass.png")
        self.sand = self._load("sand.png")
        self.ocean = self._load("ocean.png")

        self.base_runway_texture = self._load("base_runway_texture.png")

        self.cockpit = self._load("cockpit_base.png")
        self.compass = self._load("compass.png")
        self.speed_dial = self._load("speed_dial.png")

        self.sun = self._load("sun.png")
        self.moon = self._load("moon.png")

        self.logo = self._load("logo.png")

        self.help_icon = self._load("help_icon.png")

        self.damage_overlays: tuple[Surface, ...] = (
            self._load("damage_1.png"),
            self._load("damage_2.png"),
            self._load("damage_3.png"),
            self._load("damage_4.png"),
            self._load("damage_5.png"),
            self._load("damage_full.png")
        )

        self.plane_icon = self._load("plane_icon.png")
        self.gps_dest_marker = self._load("gps_dest_marker.png")

        self.cloud_blob = self._load("cloud_blob.png")

        self.augment()

    def augment(self):
        self.speed_dial = scale(self.speed_dial, (250, 250))
        self.compass = scale(self.compass, (250, 250))
        self.logo = scale_by(self.logo, 0.2)
        self.plane_icon = scale(self.plane_icon, (24, 24))
        self.gps_dest_marker = scale(self.gps_dest_marker, (24, 24))
        self.help_icon = scale(self.help_icon, (50, 50))

    def _load(self, name: str):
        return pg.image.load(paths.IMAGES_DIR / name).convert_alpha()

class Sounds(AssetBank):
    def __init__(self) -> None:
        # UI
        self.click: Sound = self._load("click.ogg")

        # Engine
        self.engine_loop_ambient: Sound = self._load("engine_loop_ambient.ogg")
        self.engine_loop_active: Sound = self._load("engine_loop_active.ogg")
        self.wind: Sound = self._load("wind.ogg")

        # Landing sounds
        self.good_landing: Sound = self._load("good_landing.ogg")
        self.hard_landing: Sound = self._load("hard_landing.ogg")
        self.crash: Sound = self._load("crash.ogg")
        self.terrain_scrape: Sound = self._load("terrain_scrape.ogg")

        # Warnings
        self.overspeed: Sound = self._load("overspeed.ogg")
        self.stall_warning: Sound = self._load("stall_warning.ogg")
        self.prohibited_zone_warning: Sound = self._load("prohibited_zone_warning.ogg")

        # Menu music
        self.menu_music: Sound = self._load("menu_music.ogg")

        self.augment()

    def augment(self):
        pass

    def _load(self, name: str) -> pg.mixer.Sound:
        return pg.mixer.Sound(paths.SOUNDS_DIR / name)

class WorldData(AssetBank):
    """Data container for raw, fixed world data."""

    def __init__(self) -> None:
        # Heightmap metadata
        with open(paths.WORLD_DIR / "height.json") as f:
            meta = json.load(f)
            self.MIN_H = meta["heights"]["min"]
            self.MAX_H = meta["heights"]["max"]
            self.SEA_LEVEL = meta["heights"]["sea_lvl"]

        # Heightmap raw data and noise
        heightmap_path = paths.WORLD_DIR / "heightmap.png"
        cached_heightmap_path = paths.CACHE_DIR / "heightmap.npy"
        paths.CACHE_DIR.mkdir(parents=True, exist_ok=True)

        if cached_heightmap_path.exists():
            # Load the cached numpy array to save time on startup
            self.height_array = np.load(cached_heightmap_path)
        else:
            # Load PNG and create numpy cache
            img = Image.open(heightmap_path)
            self.height_array = np.array(img, dtype=np.float32)
            np.save(cached_heightmap_path, self.height_array)

        self.noise = pg.image.load(paths.WORLD_DIR / "noise.png").convert_alpha()

        self.runway_data: list = cast(list, self._load_json("runways.json", "runways"))
        self.building_defs: dict = cast(dict, self._load_json("building_defs.json", "building_defs"))
        self.building_placements: list = cast(list, self._load_json("building_placements.json", "buildings"))
        self.prohibited_zones: list = cast(list, self._load_json("prohibited_zones.json", "prohibited_zones"))
        self.starfield_data: dict = cast(dict, self._load_json("starfield_data.json", "starfield"))

    def _load(self, name: str) -> Path:
        return paths.WORLD_DIR / name

    def _load_json(self, name: str, key: str) -> dict | list:
        with open(paths.WORLD_DIR / name, "r", encoding="utf-8") as f:
            return json.load(f)[key]

class ConfigPresets(AssetBank):
    """Data container for presets such as clouds that
    can be chosen by the user, but are not absolutely
    immutable, such as terrain or buildings."""

    def __init__(self) -> None:
        # Cloud data
        with open(paths.PRESETS_DIR / "cloud_configs.json") as f:
            self.cloud_configs: list = json.load(f)["cloud_configs"]

    def _load(self, name: str) -> Path:
        return paths.PRESETS_DIR / name

class TextAssets(AssetBank):
    """Data container for text-based assets"""

    COMMENT_SYMBOL = '#'
    SPACES_PER_INDENT = 4

    def __init__(self) -> None:
        self.briefing_text: list[str] = self._load("briefing.txt")

        raw_lines: list[str] = self._load("help.txt", cmt_symbol="//")
        self.help_lines: list[FLine] = []

        Style = FLine.Style
        for i, line in enumerate(raw_lines, start=1):
            # TODO: fix line counting for error messages

            stripped = line.lstrip(' ')
            leading_ws = line[:len(line) - len(stripped)]

            if '\t' in leading_ws:
                raise IndentationError(
                    f"Line {i}: Tabs are not allowed in help.txt; use {TextAssets.SPACES_PER_INDENT} spaces per indent."
                )

            num_leading_spaces = len(leading_ws)

            if num_leading_spaces % TextAssets.SPACES_PER_INDENT != 0:
                raise IndentationError(f"Line {i}: Expected {TextAssets.SPACES_PER_INDENT} spaces per indent, got {num_leading_spaces} leading spaces.")

            indentation_lvl = num_leading_spaces // TextAssets.SPACES_PER_INDENT

            if stripped.startswith('##'):
                fline = FLine(stripped[2:].strip(), indentation_lvl, Style.HEADING_2)
            elif stripped.startswith('#'):
                fline = FLine(stripped[1:].strip(), indentation_lvl, Style.HEADING_1)
            elif stripped.startswith('*'):
                fline = FLine(stripped[1:].strip(), indentation_lvl, Style.BULLET)
            else:
                fline = FLine(stripped.strip(), indentation_lvl, Style.NORMAL)

            self.help_lines.append(fline)

    def _load(self, name: str, /, *, cmt_symbol: str = COMMENT_SYMBOL) -> list[str]:
        with open(paths.TEXT_DIR / name, "r", encoding="utf-8") as f:
            return [
                line.rstrip("\n")
                for line in f if not line.lstrip().startswith(cmt_symbol)
            ]

class Assets:
    def __init__(self) -> None:
        self.images: Images = Images()
        self.fonts: Fonts = Fonts()
        self.sounds: Sounds = Sounds()
        self.world: WorldData = WorldData()
        self.config_presets: ConfigPresets = ConfigPresets()
        self.texts: TextAssets = TextAssets()
