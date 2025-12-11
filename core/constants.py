from pathlib import Path
"""Program constants"""

FPS = 60
TPS = 60
WN_W = 1350
WN_H = 850

GROUND_SIZE = 10000

INNER_RENDER_LIMIT = 0.1
OUTER_RENDER_LIMIT = 100000

BASE_DIR: Path = Path(__file__).resolve().parent.parent