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

from pathlib import Path

from pygame.font import Font

from pylines.core.custom_types import Surface
from pylines.core.utils import draw_text

DEBUG_FONT_SIZE = 28

class DebugLog:
    """A class to manage a debug log, allowing for adding messages, pruning old messages, and clearing the log."""

    def __init__(self, *, font: Font | Path) -> None:
        self.font = font
        self.contents: list[str] = []

    def write(self, message: str, /) -> None:
        """Writes a message to the debug log."""
        self.contents.append(message)

    def prune(self, *, max_len: int = 20) -> None:
        """Prunes the debug log to the specified maximum length."""
        if max_len < 0 or not isinstance(max_len, int):
            raise ValueError("max_len must be a positive integer.")

        if max_len == 0:
            raise ValueError("use clear() to clear the debug log instead of setting max_len to 0.")

        del self.contents[:-max_len]  # Keep only the most recent `max_len` entries

    def clear(self) -> None:
        """Clears the debug log."""
        self.contents.clear()

    def draw(self, surface: Surface, font_family: Font | Path | None = None, font_size: int = DEBUG_FONT_SIZE) -> None:
        """Draws the debug log contents onto the given surface."""
        y = font_size + 10  # Start drawing from the top of the surface

        if font_family is None:
            font_family = self.font  # Use the instance's font if no font family is provided

        for line in self.contents:
            draw_text(surface, (10, y), 'left', 'centre', line, (255, 255, 255), font_size, font_family)
            y += font_size  # Move down for next line
