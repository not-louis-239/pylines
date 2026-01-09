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

import pygame as pg
from pygame.transform import scale, scale_by

from .constants import BASE_DIR
from .custom_types import Sound


class AssetBank:
    """Mental basis for all asset containers."""

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
        return BASE_DIR / "assets" / "fonts" / name

class Images(AssetBank):
    def __init__(self):
        self.test_map = self._load("test_map.png")
        self.test_grass = self._load("test_grass.png")
        self.cockpit = self._load("cockpit_base.png")
        self.compass = self._load("compass.png")
        self.speed_dial = self._load("speed_dial.png")
        self.logo = self._load("logo.png")

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
        return pg.image.load(BASE_DIR / "assets" / "images" / name).convert_alpha()

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
        return pg.mixer.Sound(BASE_DIR / "assets" / "sounds" / name)

class Assets:
    def __init__(self) -> None:
        self.images: Images = Images()
        self.fonts: Fonts = Fonts()
        self.sounds: Sounds = Sounds()
