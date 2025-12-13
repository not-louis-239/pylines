from pathlib import Path
from dataclasses import dataclass
"""Program constants"""

@dataclass
class PlaneModel:
    name: str
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
CAMERA_OFFSET_Y: float = 0.1  # Offset camera or else ground will not render, in metres

# Physics
PLANE_MODEL: PlaneModel = PlaneModel(
    name="Cessna 172",
    cl_max=1.2,
    cd_min=0.03,
    cd_slope=0.0015,
    stall_angle=15,
    wing_area=16.2,
    mass=850,
    max_throttle=1200,  # DEBUG value, must set back to 1200
    aspect_ratio=7.5,
    efficiency=0.8,
    v_ne=82.31
)

AIR_DENSITY = 1.225  # kg/m³
GRAVITY = 9.8        # m/s²

# File loading
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Mathematical
EPSILON = 0.001  # Treat anything smaller than this as zero

# Visual
CHEVRON_ANGLE = 40
CHEVRON_COLOUR = (255, 0, 0)
