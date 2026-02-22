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

"""paths.py - this module acts as storage for path constants."""

from pathlib import Path

ROOT_DIR: Path = Path(__file__).resolve().parents[3]  # project root

class DirsContainer:
    def __init__(self, root: Path) -> None:
        self.root = root

    def __fspath__(self) -> str:
        return str(self.root)

    def __truediv__(self, other: str):
        """Allows DirsContainer objects to behave like Path objects
        when combined with strings."""
        return self.root / other

class AssetDirs(DirsContainer):
    def __init__(self, root: Path):
        super().__init__(root)
        self.fonts = root / "fonts"
        self.images = ImageDirs(root / "images")
        self.sounds = SoundDirs(root / "sounds")
        self.world = root / "world"
        self.presets = root / "presets"
        self.text = root / "text"

class ImageDirs(DirsContainer):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.menu_images = root / "menu_images"

class SoundDirs(DirsContainer):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.jukebox_tracks = root / "jukebox_tracks"

class DataDirs(DirsContainer):
    def __init__(self, root: Path):
        super().__init__(root)
        self.screenshots = root / "screenshots"

class SrcDirs(DirsContainer):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.shaders = root / "shaders"

class Dirs(DirsContainer):
    def __init__(self, root: Path):
        super().__init__(root)
        self.assets = AssetDirs(root / "assets")
        self.data = DataDirs(root / "save_data")
        self.cache = root / "cache"
        self.src = SrcDirs(root / "src" / "pylines")

DIRECTORIES = Dirs(ROOT_DIR)
