import pygame as pg
from core.custom_types import Surface

class Entity:
    def __init__(self, x, y, image: Surface) -> None:
        self.pos = pg.Vector2(x, y)
        self.image = image
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        pass

    def draw(self, wn: Surface):
        wn.blit(self.image, self.rect)

class Plane:
    def __init__(self):
        self.pos = pg.Vector3(0, 0, 0)
        self.vel = pg.Vector3(0, 0, 0)
        self.acc = pg.Vector3(0, 0, 0)

        self.pitch = 0
        self.yaw = 0
        self.roll = 0

        self.throttle = 0
        self.flaps = 0
        self.engine_on = True
