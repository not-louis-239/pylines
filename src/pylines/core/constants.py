from dataclasses import dataclass
from pathlib import Path

"""Program constants"""

@dataclass
class PlaneModel:
    # Coefficients
    cl_max: float
    cd_min: float
    cd_slope: float      # per degree of AoA
    # Other physics stuff
    stall_angle: float   # in degrees
    wing_area: float     # m²
    mass: float          # kg
    max_throttle: float  # Newtons
    aspect_ratio: float
    efficiency: float
    # Flaps and rudder
    flap_lift_bonus: float
    flap_drag_penalty: float
    rudder_sensitivity: float
    rudder_roll_effect: float
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
GROUND_SIZE = 100_000

PRACTISE_LIMIT = GROUND_SIZE * 0.95  # The user is "unauthorised" to go further

# Rendering
INNER_RENDER_LIMIT = 0.05
OUTER_RENDER_LIMIT = 100000
CAMERA_OFFSET_Y: float = 0.2  # Offset camera or else ground will not render, in metres

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
        flap_lift_bonus=0.3,       # +30% lift when fully extended
        flap_drag_penalty=0.5,     # +50% drag when fully extended
        rudder_sensitivity=50.0,   # torque factor applied per second
        rudder_roll_effect=5.0     # small roll caused by rudder deflection
    )
}

# Add dictionary keys to plane models as canon names
for model_name, model_data in PLANE_MODELS.items():
    model_data.name = model_name

AIR_DENSITY = 1.225  # kg/m³
GRAVITY = 9.8        # m/s²

# File loading
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent

# Mathematical
EPSILON = 0.001  # Treat anything smaller than this as zero

# Visual
CHEVRON_ANGLE = 40
CHEVRON_COLOUR = (255, 0, 0)
