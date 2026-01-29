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

"""This module acts as storage for path constants.
It should only be imported using 'import ... as paths'
so that variables don't go loose and pollute a
module's namespace."""

from pathlib import Path

ROOT_DIR: Path = Path(__file__).resolve().parents[3]  # project root

ASSETS_DIR: Path = ROOT_DIR / "assets"

CACHE_DIR: Path = ROOT_DIR / "cache"
DATA_DIR: Path = ROOT_DIR / "save_data"

FONTS_DIR: Path = ASSETS_DIR / "fonts"
IMAGES_DIR: Path = ASSETS_DIR / "images"
SOUNDS_DIR: Path = ASSETS_DIR / "sounds"
WORLD_DIR: Path = ASSETS_DIR / "world"
PRESETS_DIR: Path = ASSETS_DIR / "presets"

SHADERS_DIR: Path = ROOT_DIR / "src" / "pylines" / "shaders"
