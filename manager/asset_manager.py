import pygame
from pathlib import Path

class AssetManager:
    def __init__(self):
        self._images = {}
        self._pilot_images = {}

    def get_image(self, filename: str) -> pygame.Surface:
        if filename not in self._images:
            path = Path("Sprites/parts") / filename
            self._images[filename] = pygame.image.load(path).convert_alpha
        return self._images[filename]

    def get_pilot_image(self, filename: str) -> pygame.Surface:
            if filename not in self.pilot_images:
                path = Path("Sprites/pilots") / filename
                self._pilot_images[filename] = pygame.image.load(path).convert_alpha
            return self._pilot_images[filename]