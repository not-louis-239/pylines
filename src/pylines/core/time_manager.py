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

import math
from datetime import datetime

import pygame as pg

from . import constants as C
from .colours import SKY_COLOUR_SCHEMES, ColourScheme, lerp_colour
from .custom_types import RealNumber
from .utils import map_value


def fetch_hour() -> float:
    """Returns a value between 0 and 24 to represent the current hour."""

    now = datetime.now()
    hour = now.hour + now.minute/60 + now.second/3_600 + now.microsecond/3_600/1e6
    return hour

def sunlight_strength_from_hour(hour: RealNumber) -> RealNumber:
    if hour < C.SUNRISE_START:
        return 0
    elif hour < C.SUNRISE_END:
        return map_value(hour, C.SUNRISE_START, C.SUNRISE_END, 0, 1)
    elif hour < C.SUNSET_START:
        return 1
    elif hour < C.SUNSET_END:
        return map_value(hour, C.SUNSET_START, C.SUNSET_END, 1, 0)
    else:
        return 0

def sky_colour_from_hour(hour: float) -> ColourScheme:
    """Returns interpolated sky colours for given hour."""

    # Local aliases
    RISE_ST = C.SUNRISE_START
    RISE_END = C.SUNRISE_END
    SET_ST = C.SUNSET_START
    SET_END = C.SUNSET_END

    # Define scheme sequence with hours, these are the start times
    keyframes = [
        (0,                      SKY_COLOUR_SCHEMES["night"]),
        (RISE_ST,                SKY_COLOUR_SCHEMES["night"]),
        ((RISE_ST+RISE_END) / 2, SKY_COLOUR_SCHEMES["sunrise"]),
        (RISE_END,               SKY_COLOUR_SCHEMES["day"]),
        (SET_ST,                 SKY_COLOUR_SCHEMES["day"]),
        ((SET_ST+SET_END) / 2,   SKY_COLOUR_SCHEMES["sunset"]),
        (SET_END,                SKY_COLOUR_SCHEMES["night"]),
        (24,                     SKY_COLOUR_SCHEMES["night"]),
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

def rotation_offset_from_hour(hour: float) -> tuple[float, float]:
    """Return the expected azimuth offset for sun and stars
    in radians, with 0 being east."""

    pi = math.pi

    azimuth = (-pi/2 + 2*pi * hour/24) % (2*pi)  # radians, with 0 = east
    elevation = math.sin((hour - 6) * (2*pi / 24))  # -1 = directly underneath, 1 = directly overhead

    return azimuth, elevation

def sun_direction_from_hour(hour: float) -> pg.Vector3:
    """Returns a normalized 3D vector representing the sun's direction."""
    azimuth, elevation = rotation_offset_from_hour(hour)

    h = (1 - elevation**2)**0.5
    direction = pg.Vector3(
        h * math.cos(azimuth),  # X
        elevation,  # Y
        -h * math.sin(azimuth)  # Z
    ).normalize()

    return direction
