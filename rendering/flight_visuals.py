import random
import math
import pygame


class VisualSprite(pygame.sprite.Sprite):
    def __init__(self, image, x, y, speed, angle_deg, direction):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.math.Vector2(x, y)

        angle_rad = math.radians(angle_deg)
        dx = math.cos(angle_rad) * direction   # direction: -1 (R->L) or 1 (L->R)
        dy = math.sin(angle_rad)
        self.velocity = pygame.math.Vector2(dx, dy) * speed

    def update(self, dt):
        self.pos += self.velocity * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def is_off_screen(self, screen_width, screen_height, margin=100):
        return (self.rect.right < -margin or self.rect.left > screen_width + margin
                or self.rect.bottom < -margin or self.rect.top > screen_height + margin)


class FlightVisuals:
    def __init__(self, height, screen_width, screen_height):
        self.BACKGROUND_SLICE_STARTS = (
            0,       # slice 1, index 0
            500,     # slice 2, index 1
            30_000,  # slice 3, index 2
            50_000,  # slice 4, index 3
            70_000,  # slice 5, index 4
            100_000, # slice 6, index 5
        )

        # Each band -> list of possible sprite keys. Swap keys for whatever
        # naming scheme you use to look up loaded pygame.Surface objects.
        self.HEIGHT_BAND_SPRITES = {
            0: ["bird_small", "bird_medium"],
            1: ["bird_medium", "kite"],
            2: ["cloud_wisp", "small_plane"],
            3: ["airliner", "contrail"],
            4: ["balloon", "glider"],
            5: ["satellite_glint", "high_cloud"],
        }

        self.sprite_images = {}  # key -> pygame.Surface, populate on load

        self.screen_width = screen_width
        self.screen_height = screen_height
        self.height = height
        self.visuals_group = pygame.sprite.Group()

    def _get_band_index(self):
        band_index = 0
        for i, start in enumerate(self.BACKGROUND_SLICE_STARTS):
            if self.height >= start:
                band_index = i
            else:
                break
        return band_index

    def _instantiate_new_visual(self):
        band_index = self._get_band_index()
        possible_sprites = self.HEIGHT_BAND_SPRITES.get(band_index, [])
        if not possible_sprites:
            return None

        sprite_key = random.choice(possible_sprites)
        image = self.sprite_images.get(sprite_key)
        if image is None:
            return None

        direction = random.choice((-1, 1))          # -1 = right-to-left, 1 = left-to-right
        angle_deg = random.uniform(-15, 15)          # slight up/down drift, tweak per band if desired
        speed = random.uniform(180, 280)              # px/sec, tweak per band for parallax feel

        spawn_y = random.uniform(0, self.screen_height)
        spawn_x = -image.get_width() if direction == 1 else self.screen_width + image.get_width()

        visual = VisualSprite(image, spawn_x, spawn_y, speed, angle_deg, direction)
        self.visuals_group.add(visual)

        print(f"Spawning {sprite_key} at band {band_index}, pos=({spawn_x:.0f},{spawn_y:.0f})")

        return visual

    def update(self, dt):
        self.visuals_group.update(dt)
        for visual in list(self.visuals_group):
            if visual.is_off_screen(self.screen_width, self.screen_height):
                visual.kill()

    def draw(self, surface):
        self.visuals_group.draw(surface)