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

from pylines.core.custom_types import Coord3, RealNumber


def point_in_cuboid(point: Coord3, cuboid_centre: Coord3, cuboid_dims: Coord3) -> bool:
    x, y, z = point
    cx, cy, cz = cuboid_centre
    dx, dy, dz = cuboid_dims

    return (cx - dx/2 <= x <= cx + dx/2 and
            cy - dy/2 <= y <= cy + dy/2 and
            cz - dz/2 <= z <= cz + dz/2)

def point_in_cylinder(point: Coord3, cylinder_centre: Coord3, radius: RealNumber, height: RealNumber) -> bool:
    # Assumes that +x = east, +z = south, +y = skyward

    x, y, z = point
    cx, cy, cz = cylinder_centre

    # Check height along +y (skyward)
    if not (cy - height/2 <= y <= cy + height/2):
        return False

    # Check radius in XZ plane
    return (x - cx)**2 + (z - cz)**2 <= radius**2

def point_in_sphere(point: Coord3, sphere_centre: Coord3, radius: RealNumber) -> bool:
    x, y, z = point
    cx, cy, cz = sphere_centre

    return (x - cx)**2 + (y - cy)**2 + (z - cz)**2 <= radius**2
