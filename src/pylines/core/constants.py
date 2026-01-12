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

"""Program constants"""

from dataclasses import dataclass
from enum import Enum

class DebugMode(Enum):
    SHOW_TERRAIN_DIAGONALS = False

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

# Visuals, tick updates and window size
FPS = 60
TPS = 60
WN_W = 1350
WN_H = 850

# Ground size
WORLD_SIZE = 100_000  # distance from origin, metres, so the world is actually 200,000m wide
TRAVEL_LIMIT = WORLD_SIZE * 0.99  # The user is "unauthorised" to go further

# Rendering
INNER_RENDER_LIMIT = 0.05
OUTER_RENDER_LIMIT = 10_000

EYE_LEVEL = 1.8  # metres above ground level
CAMERA_OFFSET_Y: float = EYE_LEVEL

# Physics
PLANE_MODELS: dict[str, PlaneModel] = {
    "Cessna 172": PlaneModel(
        cl_max=1.2,
        cd_min=0.03,
        cd_slope=0.0015,
        stall_angle=15,
        wing_area=16.2,
        mass=850,
        max_throttle=1800,
        aspect_ratio=7.5,
        efficiency=0.8,
        v_ne=82.31,
        flap_lift_bonus=0.3,
        flap_drag_penalty=0.5,
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
