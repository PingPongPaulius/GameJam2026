from typing import Optional
from enum import Enum, auto

import pygame

from Tokens.token import Token, Player, Platform
from UI import Button
from anime import Animation

from rocket.part_data import PART_CATALOG
from rocket.pilot import Pilot, PilotAttributes
from rocket.rocket import Rocket
from rocket.build_area import BuildArea
from ui.part_palette import PartPalette
from ui.rocket_debug_panel import RocketDebugPanel
from scenes.build_scene import BuildScene
from rendering.rocket_renderer import draw_rocket

pygame.init()
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 1000

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
FPS = 60
dt = 0


class Phase(Enum):
    BUILD = auto()
    FLIGHT = auto()


class InstanceWrapper:

    def __init__(self, instance, pos):
        self.x = pos[0]
        self.y = pos[1]
        self.instance = instance

    def get_pos(self):
        return (self.x, self.y)


phase = Phase.BUILD

tokens = []

camera_scroll_speed = 1
half_camera_boundry = 200

loader = Animation()
exit_button = Button(0, 0, 100, 40, label="Exit")
exit_button.active = True

class AnimationAssetAdapter:
    def __init__(self, animation_loader: Animation, sprite_dir="Sprites/parts/", default_size=(64, 64)):
        self.loader = animation_loader
        self.sprite_dir = sprite_dir
        self.default_size = default_size
        self._cache = {}

    def get_image(self, filename: str):
        if filename not in self._cache:
            w, h = self.default_size
            frames = self.loader.load_sprites(f"{self.sprite_dir}{filename}", w, h, 1)
            self._cache[filename] = frames[0] if isinstance(frames, (list, tuple)) else frames
        return self._cache[filename]


slot_height = 64
slot_count = 20
horizontal_snap_points = 8
build_countdown_seconds = 10
show_rocket_debug = True
enable_snap_draws = False

assets = AnimationAssetAdapter(loader)
pilot = Pilot(name="Player One", attributes=PilotAttributes(fuel_consumption=1.0))
rocket = Rocket(pilot)
palette = PartPalette(
    list(PART_CATALOG.values()),
    assets,
)
build_area = BuildArea(
    anchor_pos=(SCREEN_WIDTH / 2, SCREEN_HEIGHT - slot_height // 2 - 24),
    slot_height=slot_height,
    slot_count=slot_count,
    horizontal_snap_points=horizontal_snap_points,
    enable_snap_draws=enable_snap_draws,
)

flight_parts = []
V = 0
camera_scroll_y = 0
_background_cache = {}


def start_flight():
    global phase, V, camera_scroll_y
    errors = rocket.validate()
    if errors:
        print("Launching anyway with issues:", errors)
    print(f"Launch! thrust={rocket.total_thrust:.0f} weight={rocket.total_weight:.0f} "
          f"stability={rocket.stability:.1f} fuel={rocket.total_fuel_capacity:.0f}")
    phase = Phase.FLIGHT
    flight_parts.clear()
    camera_scroll_y = 0
    V = 0
    for instance in build_scene.rocket.parts:
        pos = build_scene.build_area.slot_screen_pos(instance.slot_index, instance.offset_x)
        flight_parts.append(InstanceWrapper(instance, pos))
        V = rocket.performance
    rocket.velocity = V


build_scene = BuildScene(
    rocket=rocket,
    palette=palette,
    build_area=build_area,
    assets=assets,
    countdown_seconds=build_countdown_seconds,
    on_timeout=start_flight,
)
rocket_debug_panel = RocketDebugPanel()


def get_all_collisions(movable) -> list:
    collisions = []
    for token in tokens:
        if token != movable and movable.collides(token):
            collisions.append(token)
    return collisions


def move(token):
    if token.velocity.x != 0:
        token.moveX(dt)
        collisions = get_all_collisions(token)
        for collision in collisions:
            if token.velocity.x > 0:
                token.hitbox.x = collision.hitbox.x - token.hitbox.w
            if token.velocity.x < 0:
                token.hitbox.x = collision.hitbox.x + collision.hitbox.w
    if token.velocity.y != 0:
        token.moveY(dt)
        collisions = get_all_collisions(token)
        for collision in collisions:
            if token.velocity.y > 0:
                if isinstance(token, Player):
                    token.is_on_ground = True
                token.hitbox.y = collision.hitbox.y - token.hitbox.h
            if token.velocity.y < 0:
                token.velocity.y = 0
                token.hitbox.y = collision.hitbox.y + collision.hitbox.h


def find_player() -> Optional[Player]:
    for token in tokens:
        if isinstance(token, Player):
            return token
    return None

def _get_background(path: str):
    if path not in _background_cache:
        _background_cache[path] = pygame.image.load(path).convert()
    return _background_cache[path]


def handle_background(phase):
    if phase == Phase.BUILD:
        background_image = _get_background("Sprites/Background_Slice_1.png")
        screen.blit(background_image, (0, 0))
        screen.blit(background_image, (SCREEN_WIDTH / 2, 0))
    elif phase == Phase.FLIGHT:
        background_image = _get_background("Sprites/Background_Slice_2.png")
        scroll_y = int(camera_scroll_y) % background_image.get_height()
        for tile_y in range(scroll_y - background_image.get_height(), SCREEN_HEIGHT, background_image.get_height()):
            screen.blit(background_image, (0, tile_y))
            screen.blit(background_image, (SCREEN_WIDTH / 2, tile_y))


def handle_camera():
    global camera_scroll_y

    if phase == Phase.FLIGHT:
        if not flight_parts:
            return
        center_y = sum(part.y for part in flight_parts) / len(flight_parts)
        if center_y < SCREEN_HEIGHT / 2 - half_camera_boundry:
            scroll = (V - camera_scroll_speed) * dt
            for part in flight_parts:
                part.y += scroll
            camera_scroll_y += scroll
        return

    player = find_player()
    if not player:
        return
    if player.hitbox.x > SCREEN_WIDTH / 2 - half_camera_boundry:
        for token in tokens:
            token.hitbox.x -= (player.speed - camera_scroll_speed)
    if player.hitbox.x < SCREEN_WIDTH / 2 + half_camera_boundry:
        for token in tokens:
            token.hitbox.x += (player.speed - camera_scroll_speed)


def frame():
    global dt, phase
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if phase == Phase.BUILD:
            build_scene.handle_event(event)

    screen.fill("gray")

    if phase == Phase.BUILD:
        handle_background(phase)
        build_scene.update(dt)
        build_scene.draw(screen)

    elif phase == Phase.FLIGHT:
        handle_background(phase)
        for instance in flight_parts:
            instance.y -= V * dt
        handle_camera()
        for instance in flight_parts:
            image = build_scene.assets.get_image(instance.instance.part_def.sprite)
            screen.blit(image, image.get_rect(center=instance.get_pos()))

    if exit_button.update() == "Pressed":
        return False
    exit_button.render(screen)

    if show_rocket_debug:
        rocket_debug_panel.draw(screen, rocket)

    pygame.display.flip()
    dt = clock.tick(FPS) / 1000
    return True


if __name__ == "__main__":
    running = True
    while running:
        running = frame()

    pygame.quit()
