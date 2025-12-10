import os
import pygame as pg

BASE_DIR = os.path.dirname(__file__)

def asset_path(name: str) -> str:
    return os.path.join(BASE_DIR, "assets", name)

def load_images() -> dict[str, pg.Surface]:
    return {
        # TODO: "bomb": pg.image.load(asset_path("bomb.png")).convert_alpha()
    }
