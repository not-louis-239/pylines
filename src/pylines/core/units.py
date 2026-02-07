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
from enum import Enum, auto

from ..core.custom_types import RealNumber


class DimensionType(Enum):
    LENGTH = auto()
    TIME = auto()
    MASS = auto()
    ANGLE = auto()

class DimensionVector:
    def __init__(self, dims: dict[DimensionType, float] | None = None) -> None:
        # Remove zero-count dimensions
        self.dims = {k: v for k, v in (dims or {}).items() if v != 0}

    def __add__(self, other: DimensionVector) -> DimensionVector:
        new_dims = self.dims.copy()

        # Loop through the other vector's dimensions
        for dim_type, exponent in other.dims.items():
            new_dims[dim_type] = new_dims.get(dim_type, 0) + exponent

        return DimensionVector(new_dims)

    def __sub__(self, other: DimensionVector) -> DimensionVector:
        new_dims = self.dims.copy()

        # Loop through the other vector's dimensions
        for dim_type, exponent in other.dims.items():
            new_dims[dim_type] = new_dims.get(dim_type, 0) - exponent

        return DimensionVector(new_dims)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DimensionVector):
            return False
        return self.dims == other.dims

    def __repr__(self) -> str:
        return f"DimensionVector({self.dims})"

@dataclass
class Unit:
    """Class to represent unit objects, e.g. metres, feet, seconds.
    They have dimensions and a scale multiplier."""

    scale: RealNumber
    dim_vec: DimensionVector

    def compatible_with(self, other: Unit) -> bool:
        return self.dim_vec == other.dim_vec

    def __mul__(self, other: Unit) -> Unit:
        return Unit(self.scale * other.scale, self.dim_vec + other.dim_vec)

    def __truediv__(self, other: Unit) -> Unit:
        return Unit(self.scale / other.scale, self.dim_vec - other.dim_vec)

    def __pow__(self, exponent: RealNumber):
        return Unit(
            self.scale ** exponent,
            DimensionVector(
                {
                    k: v * exponent for k, v in self.dim_vec.dims.items()
                }
            )
        )

# Multiplicative identity
SCALAR = Unit(1, DimensionVector())  # no dimensions

# Length
METRES = Unit(1, DimensionVector({DimensionType.LENGTH: 1}))
KILOMETRES = Unit(1_000, METRES.dim_vec)
FEET = Unit(0.3048, METRES.dim_vec)
NAUTICAL_MI = Unit(1_852, METRES.dim_vec)

# Time
SECONDS = Unit(1, DimensionVector({DimensionType.TIME: 1}))
MINUTES = Unit(60, SECONDS.dim_vec)
HOURS = Unit(3_600, SECONDS.dim_vec)
DAYS = Unit(86_400, SECONDS.dim_vec)

# Mass
KILOGRAMS = Unit(1, DimensionVector({DimensionType.MASS: 1}))

# Angle
RADIANS = Unit(1, DimensionVector({DimensionType.ANGLE: 1}))
DEGREES = Unit(math.pi / 180, RADIANS.dim_vec)
ARCMINUTES = Unit(DEGREES.scale / 60, RADIANS.dim_vec)
ARCSECONDS = Unit(DEGREES.scale / 3_600, RADIANS.dim_vec)

# Speed
KNOTS = NAUTICAL_MI / HOURS
KM_PER_H = KILOMETRES / HOURS

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
        raise ValueError(f"Incompatible units: {unit_in.dim_vec} -> {unit_out.dim_vec}")

    return value * unit_in.scale / unit_out.scale

def _main():
    """Test code"""

    print("=== Base Unit Conversions ===")
    # Length
    print(f"1 metre = {convert_units(1, METRES, FEET):.3f} feet")
    print(f"1 kilometre = {convert_units(1, KILOMETRES, METRES):.0f} metres")

    # Time
    print(f"1 hour = {convert_units(1, HOURS, MINUTES):.0f} minutes")
    print(f"1 day = {convert_units(1, DAYS, HOURS):.0f} hours")

    # Angle
    print(f"90 degrees = {convert_units(90, DEGREES, RADIANS):.3f} radians")
    print(f"1 arcsecond = {convert_units(1, ARCSECONDS, RADIANS):.6f} radians")

    print("\n=== Derived Units ===")
    # Speed
    speed_m_per_s = 100  # 100 m/s
    speed_km_per_h = convert_units(speed_m_per_s, METRES/SECONDS, KM_PER_H)
    print(f"100 m/s = {speed_km_per_h:.2f} km/h")

    speed_knots = 20  # 20 knots
    speed_m_per_s = convert_units(speed_knots, KNOTS, METRES/SECONDS)
    print(f"20 knots = {speed_m_per_s:.2f} m/s")

    # Force
    force_value = 10  # 10 N
    force_scale = convert_units(force_value, NEWTONS, NEWTONS)
    print(f"10 N = {force_scale:.2f} N (dim: {NEWTONS.dim_vec})")

    print("\n=== Powers ===")
    area_unit = METRES**2
    volume_unit = METRES**3
    print(f"Area unit (m²): {area_unit.dim_vec}")
    print(f"Volume unit (m³): {volume_unit.dim_vec}")

    print("\n=== Compatibility Checks ===")
    print(f"METRES compatible with FEET? {METRES.compatible_with(FEET)}")
    print(f"METRES compatible with SECONDS? {METRES.compatible_with(SECONDS)}")

    # Convert 10 m² to cm²
    area_m2_value = 10
    cm_unit = Unit(0.01, METRES.dim_vec)  # 1 cm = 0.01 m
    area_cm2 = convert_units(area_m2_value, METRES**2, cm_unit**2)
    print(f"10 m² = {area_cm2:.0f} cm²")

if __name__ == "__main__":
    _main()
