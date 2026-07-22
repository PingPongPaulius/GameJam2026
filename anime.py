import pygame
from typing import Optional

class Animation_Obj:

    def __init__(self, anime, speed):
        self.anime = anime
        self.speed = speed


class Animation:

    def __init__(self):
        self.animations = {}
        self.curr = 0
        self.timer = 0
        self.animation = ''

    def add(self, name: str, sprite_path: str, w: int = 16, h: int = 16, speed: int = 1, scale: float = 1):

        if name in self.animations:
            print(f"[DEBUG anime] HEY! {name} is already in animations!!!!")
        sprites = self.load_sprites(sprite_path, w, h, scale)
        self.animations[name] = Animation_Obj(sprites, speed)
        self.animation = name

    def load_sprites(self, filename: str, w:int, h: int, scale: float):
        sheet = pygame.image.load(filename).convert_alpha()
        x = 0
        sprites = []
        while x + w <= sheet.get_width():
            area = (x, 0, w, h)
            sprites.append(self.load_sprite(area, sheet, w, h, scale))
            x += w
        return sprites

    def load_sprite(self, region, sprite_sheet, w, h, s):
        rect = pygame.Rect(region)
        image = pygame.Surface(rect.size, pygame.SRCALPHA)
        image.blit(sprite_sheet, (0,0), rect)
        image = pygame.transform.scale(image, (int(w*s), int(h*s)))
        return image
    
    def get_curr_animation(self) -> Optional[Animation_Obj]:
        return self.animations.get(self.animation, None)
    

    def step(self, dt: float):
        self.timer += dt
        anime = self.get_curr_animation()
        if self.timer > anime.speed:
            self.curr = (self.curr + 1) % len(anime.anime)
            self.timer = 0
    
    def switch_to(self, animation_name: str):
        if animation_name in self.animations:
            self.animation = animation_name
            self.reset()

    def reset(self):
        self.curr = 0
        self.timer = 0

    def curr_frame(self, flip_h=False, flip_v=False):
        img = self.get_curr_animation().anime[self.curr]
        return pygame.transform.flip(img, flip_h, flip_v)
