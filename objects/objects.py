import pygame as pg
from core.constants import Surface

class Entity:
    def __init__(self, x, y, image: Surface) -> None:
        self.pos = pg.Vector2(x, y)
        self.image = image
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        pass

    def draw(self, wn: Surface):
        wn.blit(self.image, self.rect)
