from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]  # project root, not filesystem root
ASSETS_DIR = ROOT_DIR / "assets"
MAPS_DIR = ASSETS_DIR / "maps"