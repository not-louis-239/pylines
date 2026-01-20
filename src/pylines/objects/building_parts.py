"""building_parts.py - contains the ingredients to make buildings"""

import pygame as pg

class BuildingPart:
    def __init__(self, off_x, off_y, off_z) -> None:
        self.offset = pg.Vector3(off_x, off_y, off_z)

    def draw(self):
        raise NotImplementedError

