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

__version__ = "0.14.0"

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
INNER_RENDER_LIMIT: float = 2.0
OUTER_RENDER_LIMIT: float = 25_000

CAMERA_RADIUS: float = 4  # The camera is a sphere collider now

# Add dictionary keys to plane models as canon names
for model_name, model_data in PLANE_MODELS.items():
    model_data.name = model_name

# Physics
AIR_DENSITY = 1.225  # kg/m³
GRAVITY = 9.8        # m/s²

# Mathematical
MATH_EPSILON = 0.0001  # Treat anything smaller than this as zero
NORMAL_CALC_EPSILON = 1.0  # Epsilon for normal calculations (in metres)

# Visual
FOV = 70  # degrees

CHEVRON_ANGLE = 40
CHEVRON_COLOUR = (255, 0, 0)

MAP_TOGGLE_ANIMATION_DURATION = 0.15  # seconds
MAP_METRES_PER_PX = 50  # metres per pixel
MAP_PIXELS_PER_TILE = 100  # pixels
METRES_PER_TILE = MAP_METRES_PER_PX * MAP_PIXELS_PER_TILE

CONTROLS_REF_TOGGLE_ANIMATION_DURATION = 0.08  # seconds
JUKEBOX_MENU_TOGGLE_ANIMATION_DURATION = 0.15

# Terrain brightness
SHADE_BRIGHTNESS_MULT = 0.5  # Brightness multiplier when shaded
MOON_BRIGHTNESS = 0.18  # Moonlight brightness (omnipresent, uniform)
SUN_BRIGHTNESS = 1.0  # Brightness in direct, full-strength sunlight

# Daylight cycle
SUNRISE_START = 4
SUNRISE_END = 8
SUNSET_START = 16
SUNSET_END = 20

# Map display
MAP_OVERLAY_SIZE = 500
MAP_ZOOM_MIN = 1
MAP_ZOOM_MAX = 100
SCALE_BAR_LENGTHS = [25, 100, 500, 1_000, 2_000, 5_000, 10_000]

# Controls
THROTTLE_SPEED = 0.7
FLAPS_SPEED = 2
RUDDER_SPEED = 2.5
RUDDER_SNAPBACK = 0.8

# Clouds
CLOUD_GRID_STEP = 800
CLOUD_MAX_DRAW_RADIUS = 8_000
CLOUD_BASE_BLOB_SIZE = 1400
CLOUD_NOISE_SCALE = 0.0004  # world -> noise space
CLOUD_BASE_ALPHA = 0.4

COMPASS_QUANTISATION_STEPS = 300

# Not for export
del _WORLD_SIZE