import pygame
from pathlib import Path

class AssetManager:
    def __init__(self):
        self._images = {}
        self._pilot_images = {}
        self._backgrounds = {}

    def get_image(self, filename: str) -> pygame.Surface:
        if filename not in self._images:
            path = Path("Sprites/parts") / filename
            self._images[filename] = pygame.image.load(path).convert_alpha()
        return self._images[filename]

    def get_pilot_image(self, filename: str) -> pygame.Surface:
            if filename not in self._pilot_images:
                path = Path("Sprites/pilots") / filename
                self._pilot_images[filename] = pygame.image.load(path).convert_alpha()
            return self._pilot_images[filename]

    def get_background(self, filename: str) -> pygame.Surface:
        if filename not in self._backgrounds:
            path = Path("Sprites") / filename
            self._backgrounds[filename] = pygame.image.load(path).convert_alpha()
        return self._backgrounds[filename]