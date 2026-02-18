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

from pygame import Surface
from pylines.core.utils import draw_text
from pylines.core.asset_manager import Fonts

DEBUG_FONT_SIZE = 14

def draw_debug_display(surf: Surface, lines: list[str], font_instance: Fonts) -> None:
    """Renders a list of lines to the given surface, with colour coding based on timing."""
    DEBUG_FONT_FAMILY = font_instance.monospaced

    y = 10
    for line in lines:
        draw_text(surf, (10, y), 'left', 'centre', line, (255, 255, 255), DEBUG_FONT_SIZE, DEBUG_FONT_FAMILY)
        y += 15  # Move down for next line
