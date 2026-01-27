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

from datetime import datetime

from .colours import SKY_COLOUR_SCHEMES, ColourScheme, lerp_colour
from .custom_types import RealNumber
from .utils import map_value


def fetch_hour() -> float:
    """Returns a value between 0 and 24 to represent the current hour."""

    now = datetime.now()
    hour = now.hour + now.minute/60 + now.second/3_600 + now.microsecond/3_600/1e6
    return hour

def brightness_from_hour(hour: RealNumber) -> RealNumber:
    """Returns the expected terrain brightness.

    0 = pitch black, 1 = full brightness"""

    MIN_BRIGHTNESS = 0.15  # moonlight
    MAX_BRIGHTNESS = 1.0  # sunlight

    if hour < 4:
        return MIN_BRIGHTNESS
    elif hour < 8:
        return map_value(hour, 4, 8, MIN_BRIGHTNESS, MAX_BRIGHTNESS)
    elif hour < 16:
        return MAX_BRIGHTNESS
    elif hour < 20:
        return map_value(hour, 16, 20, MAX_BRIGHTNESS, MIN_BRIGHTNESS)
    else:
        return MIN_BRIGHTNESS

def sky_colour_from_hour(hour: float) -> ColourScheme:
    """Returns interpolated sky colours for given hour."""

    # Define scheme sequence with hours, these are the start times
    keyframes = [
        (0, SKY_COLOUR_SCHEMES["night"]),
        (4, SKY_COLOUR_SCHEMES["night"]),
        (6, SKY_COLOUR_SCHEMES["sunrise"]),
        (8, SKY_COLOUR_SCHEMES["day"]),
        (16, SKY_COLOUR_SCHEMES["day"]),
        (18, SKY_COLOUR_SCHEMES["sunset"]),
        (20, SKY_COLOUR_SCHEMES["night"]),
        (24, SKY_COLOUR_SCHEMES["night"]),
    ]

    # Find surrounding keyframes
    for i in range(len(keyframes) - 1):
        start_hour, start_scheme = keyframes[i]
        end_hour, end_scheme = keyframes[i+1]
        if start_hour <= hour <= end_hour:
            t = (hour - start_hour) / (end_hour - start_hour)
            return ColourScheme(
                high=lerp_colour(start_scheme.high, end_scheme.high, t),
                mid=lerp_colour(start_scheme.mid, end_scheme.mid, t),
                low=lerp_colour(start_scheme.low, end_scheme.low, t),
            )
    return SKY_COLOUR_SCHEMES["night"]  # fallback
