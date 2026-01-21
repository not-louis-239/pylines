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

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.custom_types import RealNumber


@dataclass(frozen=True, kw_only=True)
class _DimensionVector:
    length: RealNumber = 0
    time: RealNumber = 0
    mass: RealNumber = 0
    angle: RealNumber = 0

    def __add__(self, other: _DimensionVector) -> _DimensionVector:
        return _DimensionVector(
            length=self.length + other.length,
            time=self.time + other.time,
            mass=self.mass + other.mass,
            angle=self.angle + other.angle,
        )

    def __sub__(self, other: _DimensionVector) -> _DimensionVector:
        return _DimensionVector(
            length=self.length - other.length,
            time=self.time - other.time,
            mass=self.mass - other.mass,
            angle=self.angle - other.angle,
        )

@dataclass(frozen=True)
class Unit:
    """Class to represent unit objects, e.g. metres, feet, seconds."""

    scale: float
    dims: _DimensionVector

    def compatible_with(self, other: Unit) -> bool:
        return self.dims == other.dims

    def __mul__(self, other: Unit) -> Unit:
        return Unit(self.scale * other.scale, self.dims + other.dims)

    def __truediv__(self, other: Unit) -> Unit:
        return Unit(self.scale / other.scale, self.dims - other.dims)

    def __pow__(self, exponent: RealNumber):
        return Unit(
            self.scale ** exponent,
            _DimensionVector(
                length=(self.dims.length * exponent),
                time=(self.dims.time * exponent),
                mass=(self.dims.mass * exponent),
                angle=(self.dims.angle * exponent),
            )
        )

# Units - root units should be listed first and used as the dimension
#         parameter for all units of same dimensions

SCALAR = Unit(1, _DimensionVector())  # multiplicative identity for units

# Length
METRES = Unit(1, _DimensionVector(length=1))
KILOMETRES = Unit(1_000, METRES.dims)
FEET = Unit(0.3048, METRES.dims)
NAUTICAL_MI = Unit(1_852, METRES.dims)

# Time
SECONDS = Unit(1, _DimensionVector(time=1))
MINUTES = Unit(60, SECONDS.dims)
HOURS = Unit(3_600, SECONDS.dims)
DAYS = Unit(86_400, SECONDS.dims)

# Mass
KILOGRAMS = Unit(1, _DimensionVector(mass=1))

# Angle
RADIANS = Unit(1, _DimensionVector(angle=1))
DEGREES = Unit(math.pi/180, RADIANS.dims)
ARCMINUTES = Unit(1/60 * DEGREES.scale, RADIANS.dims)
ARCSECONDS = Unit(1/3_600 * DEGREES.scale, RADIANS.dims)

# Speed
KNOTS = NAUTICAL_MI/HOURS

# Force
NEWTONS = KILOGRAMS * METRES / SECONDS**2

def convert_units(value: RealNumber, unit_in: Unit, unit_out: Unit, /) -> RealNumber:
    """
    Convert a value from one unit to another unit

    Args:
        value        Number of input units to convert
        unit_in      The unit to be converted from, e.g. metres per second
        unit_out     The unit to be converted to, e.g. feet per minute

    Returns:
        RealNumber (type-aliased to int | float)
                     Measured in unit_out.
    """

    if not unit_in.compatible_with(unit_out):
        raise ValueError(f"Incompatible units: {unit_in.dims} -> {unit_out.dims}")
    return value * unit_in.scale / unit_out.scale

def _main():
    print("Test: Converting 5 m/s to km/h:")
    print("Output:", convert_units(5, METRES/SECONDS, KILOMETRES/HOURS))
    print("Testing exponentiation: seconds^2")
    print("Output:", SECONDS**2)

if __name__ == "__main__":
    _main()