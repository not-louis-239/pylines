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

from pathlib import Path
import json
from PIL import Image
import numpy as np

import pygame as pg
from pygame.transform import scale, scale_by

from .paths import ROOT_DIR
from .constants import GROUND_SIZE
from .custom_types import Sound
from .utils import map_value

class AssetBank:
    """Base class to store assets."""

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
        self.monospaced: Path = self._load("Inconsolata-VariableFont_wdth,wght.ttf")
        self.augment()

    def _load(self, name: str) -> Path:
        return ROOT_DIR / "assets" / "fonts" / name

class Images(AssetBank):
    def __init__(self):
        self.test_grass = self._load("test_grass.png")
        self.cockpit = self._load("cockpit_base.png")
        self.compass = self._load("compass.png")
        self.speed_dial = self._load("speed_dial.png")
        self.logo = self._load("logo.png")
        self.sun = self._load("sun.png")
        self.moon = self._load("moon.png")

        self.damage_overlays: tuple = (
            self._load("damage_1.png"),
            self._load("damage_2.png"),
            self._load("damage_3.png"),
            self._load("damage_4.png"),
            self._load("damage_5.png"),
            self._load("damage_full.png")
        )

        self.augment()

    def augment(self):
        self.speed_dial = scale(self.speed_dial, (250, 250))
        self.compass = scale(self.compass, (250, 250))
        self.logo = scale_by(self.logo, 0.2)

    def _load(self, name: str):
        return pg.image.load(ROOT_DIR / "assets" / "images" / name).convert_alpha()

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
        self.menu_music: Sound = self._load("menu_music.ogg")

        self.augment()

    def augment(self):
        self.good_landing.set_volume(10)

    def _load(self, name: str) -> pg.mixer.Sound:
        return pg.mixer.Sound(ROOT_DIR / "assets" / "sounds" / name)

class Assets:
    def __init__(self) -> None:
        self.images: Images = Images()
        self.fonts: Fonts = Fonts()
        self.sounds: Sounds = Sounds()
        self.map: MapData = MapData()

class MapData(AssetBank):
    def __init__(self) -> None:
        with open(ROOT_DIR / "assets/map/height.json") as f:
            meta = json.load(f)
            self.MIN_H = meta["heights"]["min"]
            self.MAX_H = meta["heights"]["max"]
            self.SEA_LEVEL = meta["heights"]["sea_lvl"]

        img_path = ROOT_DIR / "assets/map/heightmap.png"
        img = Image.open(img_path)
        self.height_array = np.array(img, dtype=np.uint16)
        self.height_surface = pg.transform.grayscale(pg.image.load(img_path))  # Load as grayscale Pygame surface
        self.width, self.height = self.height_surface.get_size()  # Store dimensions
        self.world_size = GROUND_SIZE # Store world size

    def get_height(self, x: float, z: float) -> float:
        # Map world coordinates (x, z) to image coordinates (ix, iy)
        # World origin (0,0) is center of heightmap.
        # Image origin (0,0) is top-left.
        ix_float = map_value(x, -self.world_size, self.world_size, 0, self.width - 1)
        iy_float = map_value(z, -self.world_size, self.world_size, 0, self.height - 1)

        # Clamp coordinates to be within image bounds
        ix_float = max(0.0, min(ix_float, self.width - 1.0001)) # ensure we don't sample outside
        iy_float = max(0.0, min(iy_float, self.height - 1.0001))

        # Get the four surrounding pixel coordinates
        x1 = int(ix_float)
        y1 = int(iy_float)
        x2 = x1 + 1
        y2 = y1 + 1

        # Get fractional parts
        fx = ix_float - x1
        fy = iy_float - y1

        # Get brightness values of the four corners
        # Ensure we don't go out of bounds
        b11 = self.height_surface.get_at((x1, y1)).r
        b12 = self.height_surface.get_at((x1, y2)).r
        b21 = self.height_surface.get_at((x2, y1)).r
        b22 = self.height_surface.get_at((x2, y2)).r

        # Bilinear interpolation
        # Interpolate along x-axis
        b_interp_x1 = b11 * (1 - fx) + b21 * fx
        b_interp_x2 = b12 * (1 - fx) + b22 * fx

        # Interpolate along y-axis
        brightness = b_interp_x1 * (1 - fy) + b_interp_x2 * fy

        # Map brightness to height
        height = map_value(brightness, 0, 255, self.MIN_H, self.MAX_H)
        return height

    def _load(self, name: str) -> Path:
        return ROOT_DIR / "assets" / "map" / name