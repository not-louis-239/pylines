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
    # Safety
    v_ne: float  # Velocity Never Exceed, in m/s
    # Name
    name: str

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
        name="Cessna 172",
        cl_max=1.2,
        cd_min=0.03,
        cd_slope=0.0015,
        stall_angle=15,
        wing_area=16.2,
        mass=850,
        max_throttle=1800,
        aspect_ratio=7.5,
        efficiency=0.8,
        v_ne=82.31
    ),
    "Piper Cub": PlaneModel(
        name="Piper Cub",
        cl_max=1.4,           # more lift, slower stall
        cd_min=0.035,         # slightly higher drag
        cd_slope=0.0018,
        stall_angle=16,       # very forgiving
        wing_area=17.0,
        mass=600,             # lighter
        max_throttle=800,     # lower thrust
        aspect_ratio=8.0,
        efficiency=0.85,
        v_ne=70.0             # slower Vne
    ),
    "Extra 300": PlaneModel(
        name="Extra 300",
        cl_max=1.1,           # moderate lift
        cd_min=0.025,         # very aerodynamic
        cd_slope=0.0020,
        stall_angle=14,       # higher stall speed
        wing_area=11.0,
        mass=950,             # heavier for inertia
        max_throttle=1600,    # higher thrust
        aspect_ratio=6.5,
        efficiency=0.75,
        v_ne=120.0            # can go much faster
    ),
    "Airbus A320": PlaneModel(
        name="Airbus A320",
        cl_max=1.5,           # airliners have decent lift at high AoA
        cd_min=0.02,          # sleek but heavier plane
        cd_slope=0.0012,      # drag rises slowly with AoA
        stall_angle=16,        # high stall angle due to wing design
        wing_area=122.6,       # typical A320 wing area in m²
        mass=73500,            # typical max takeoff weight in kg
        max_throttle=120000,   # roughly engines’ combined thrust in N
        aspect_ratio=9.0,      # moderate aspect ratio
        efficiency=0.85,       # wing efficiency
        v_ne=250.0             # never exceed speed (approx 900 km/h)
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
