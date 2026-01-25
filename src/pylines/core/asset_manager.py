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
from pathlib import Path

import numpy as np
import pygame as pg
from PIL import Image
from pygame.transform import scale, scale_by

from pylines.core.custom_types import Sound
import pylines.core.paths as paths

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

        self.cockpit = self._load("cockpit_base.png")
        self.compass = self._load("compass.png")
        self.speed_dial = self._load("speed_dial.png")

        self.sun = self._load("sun.png")
        self.moon = self._load("moon.png")

        self.logo = self._load("logo.png")

        self.damage_overlays: tuple = (
            self._load("damage_1.png"),
            self._load("damage_2.png"),
            self._load("damage_3.png"),
            self._load("damage_4.png"),
            self._load("damage_5.png"),
            self._load("damage_full.png")
        )

        self.plane_icon = self._load("plane_icon.png")
        self.gps_dest_marker = self._load("gps_dest_marker.png")

        self.augment()

    def augment(self):
        self.speed_dial = scale(self.speed_dial, (250, 250))
        self.compass = scale(self.compass, (250, 250))
        self.logo = scale_by(self.logo, 0.2)
        self.plane_icon = scale(self.plane_icon, (24, 24))
        self.gps_dest_marker = scale(self.gps_dest_marker, (24, 24))

    def _load(self, name: str):
        return pg.image.load(paths.IMAGES_DIR / name).convert_alpha()

class Sounds(AssetBank):
    def __init__(self) -> None:
        # UI
        self.click: Sound = self._load("click.ogg")

        # Engine
        self.engine_idle_loop: Sound = self._load("engine_idle_loop.ogg")
        self.engine_20p_loop: Sound = self._load("engine_20p_loop.ogg")
        self.engine_40p_loop: Sound = self._load("engine_40p_loop.ogg")
        self.engine_60p_loop: Sound = self._load("engine_60p_loop.ogg")
        self.engine_80p_loop: Sound = self._load("engine_80p_loop.ogg")
        self.engine_full_loop: Sound = self._load("engine_full_loop.ogg")

        # Landing sounds
        self.good_landing: Sound = self._load("good_landing.ogg")
        self.hard_landing: Sound = self._load("hard_landing.ogg")
        self.crash: Sound = self._load("crash.ogg")

        # Warnings
        self.overspeed: Sound = self._load("overspeed.ogg")
        self.stall_warning: Sound = self._load("stall_warning.ogg")
        self.prohibited_zone_warning: Sound = self._load("prohibited_zone_warning.ogg")

        # Menu music
        self.menu_music: Sound = self._load("menu_music.ogg")

        self.augment()

    def augment(self):
        self.good_landing.set_volume(10)

    def _load(self, name: str) -> pg.mixer.Sound:
        return pg.mixer.Sound(paths.SOUNDS_DIR / name)

class WorldData(AssetBank):
    """Data container for raw world data."""

    def __init__(self) -> None:
        # Heightmap metadata
        with open(paths.WORLD_DIR / "height.json") as f:
            meta = json.load(f)
            self.MIN_H = meta["heights"]["min"]
            self.MAX_H = meta["heights"]["max"]
            self.SEA_LEVEL = meta["heights"]["sea_lvl"]

        # Heightmap raw data and noise
        img_path = paths.WORLD_DIR / "heightmap.png"
        img = Image.open(img_path)
        self.height_array = np.array(img, dtype=np.float32)

        self.noise = pg.image.load(paths.WORLD_DIR / "noise.png").convert_alpha()

        # Runway data
        with open(paths.WORLD_DIR / "runways.json") as f:
            self.runway_data: list = json.load(f)["runways"]

        # Building definitions
        with open(paths.WORLD_DIR / "building_defs.json") as f:
            self.building_defs: dict = json.load(f)["building_defs"]

        # Building placements
        with open(paths.WORLD_DIR / "building_placements.json") as f:
            self.building_placements: dict = json.load(f)["buildings"]

        # Prohibited zones
        with open(paths.WORLD_DIR / "prohibited_zones.json") as f:
            self.prohibited_zones: dict = json.load(f)["prohibited_zones"]

    def _load(self, name: str) -> Path:
        return paths.WORLD_DIR / name

class Assets:
    def __init__(self) -> None:
        self.images: Images = Images()
        self.fonts: Fonts = Fonts()
        self.sounds: Sounds = Sounds()
        self.world: WorldData = WorldData()
