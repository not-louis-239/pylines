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

"""Program constants"""

from dataclasses import dataclass
from enum import IntEnum


@dataclass
class PlaneModel:
    # Fundamental coefficients
    cl_max: float
    cd_min: float
    cd_slope: float      # per degree of AoA
    # Physics
    stall_angle: float   # in degrees
    wing_area: float     # m²
    mass: float          # kg
    max_throttle: float  # Newtons
    aspect_ratio: float
    efficiency: float
    roll_stability_factor: float  # how much the plane "wants" to level out; less -> allows steeper banking
    # Flaps and rudder
    flap_lift_bonus: float     # decimal, e.g. 0.3 = +30%
    flap_drag_penalty: float   # decimal, e.g. 0.3 = +30%
    rudder_sensitivity: float  # torque factor applied per second
    rudder_roll_effect: float  # small roll from rudder deflection
    max_bank_angle: float      # beyond this, rudder won't cause extra roll
    # Safety
    v_ne: float  # Velocity Never Exceed, in m/s
    # Name
    name: str = "UnnamedModel"  # Name is currently owned by the list of PLANE_MODELS

class SFXChannelID(IntEnum):
    # Music
    MUSIC = 0

    # Engine
    ENGINE_AMBIENT = 1
    ENGINE_ACTIVE = 2
    WIND = 3

    # Warnings
    STALL = 4
    OVERSPEED = 5
    PROHIBITED = 6

# Visuals, tick updates and window size
FPS = 60
TPS = 60
WN_W = 1350
WN_H = 850

# Ground size
_WORLD_SIZE = 200_000  # metres
HALF_WORLD_SIZE = _WORLD_SIZE // 2  # distance from origin, metres, so the world is actually 200,000m wide
HARD_TRAVEL_LIMIT = HALF_WORLD_SIZE * 0.99  # invisible wall
SOFT_TRAVEL_LIMIT = HALF_WORLD_SIZE * 0.95  # past this, forces push the user back into the centre

# Rendering
INNER_RENDER_LIMIT = 0.05
OUTER_RENDER_LIMIT = 50_000

CAMERA_RADIUS: float = 4  # The camera is a sphere collider now

# Plane models - these should eventually be moved to a separate file called `plane_models.py`
PLANE_MODELS: dict[str, PlaneModel] = {
    "Cessna 172": PlaneModel(
        cl_max=1.2,
        cd_min=0.03,
        cd_slope=0.0015,
        stall_angle=15,
        wing_area=16.2,
        mass=850,
        max_throttle=1500,
        aspect_ratio=7.5,
        efficiency=0.8,
        v_ne=82.31,
        flap_lift_bonus=0.3,
        flap_drag_penalty=0.6,
        rudder_sensitivity=50.0,
        rudder_roll_effect=5.0,
        roll_stability_factor=0.1,
        max_bank_angle=30
    )
}

# Add dictionary keys to plane models as canon names
for model_name, model_data in PLANE_MODELS.items():
    model_data.name = model_name

AIR_DENSITY = 1.225  # kg/m³
GRAVITY = 9.8        # m/s²

# Mathematical
EPSILON = 0.0001  # Treat anything smaller than this as zero

# Visual
CHEVRON_ANGLE = 40
CHEVRON_COLOUR = (255, 0, 0)

MAP_TOGGLE_ANIMATION_DURATION = 0.15  # seconds
MAP_METRES_PER_PX = 50  # metres per pixel
MAP_PIXELS_PER_TILE = 100  # pixels
METRES_PER_TILE = MAP_METRES_PER_PX * MAP_PIXELS_PER_TILE
