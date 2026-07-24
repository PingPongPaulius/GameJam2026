import glob
import re
import random as rng
from typing import Optional
from enum import Enum, auto

import pygame

from Tokens.token import Token, Player, Platform
from UI import Button
from anime import Animation

from rocket.part_data import PART_CATALOG
from rocket.pilot import Pilot, PilotAttributes
from rocket.pilot_data import PILOT_CATALOG
from rocket.rocket import Rocket
from rocket.build_area import BuildArea
from ui.build_sidebar import BuildSidebar
from ui.rocket_debug_panel import RocketDebugPanel
from ui.slide_cover import SlideCover
from scenes.build_scene import BuildScene
from rendering.rocket_renderer import draw_rocket
from vector import Vector

pygame.init()
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 1000
BG_COLOR = (20, 20, 20)

# Get the desktop size and set the screen size to 80% of it
desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
SCREEN_WIDTH = int(desktop_w * 0.8)
SCREEN_HEIGHT = int(desktop_h * 0.8)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
FPS = 60
dt = 1/FPS


class Phase(Enum):
    BUILD = auto()
    FLIGHT = auto()


class InstanceWrapper:

    def __init__(self, instance, pos):
        self.x = pos[0]
        self.y = pos[1]
        self.instance = instance
        self.vector = Vector(self.x, self.y)
        self.FALL_X = 0

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

# Variables for the build area and the rocket
slot_height = 64
slot_count = 20
horizontal_snap_points = 8

# Countdown for the launch
build_countdown_seconds = 10
elapsed = 0.0
_locked = False

# Debug options
show_rocket_debug = True
enable_snap_draws = False

assets = AnimationAssetAdapter(loader)
pilots = PILOT_CATALOG

if rng.randint(1, 100) > 99:
    selected_pilot = 4
else:
    selected_pilot = rng.randint(1,3)

pilot = Pilot(
    name=pilots[selected_pilot].name,
    attributes=PilotAttributes(**pilots[selected_pilot].attributes),
    portrait_sprite=pilots[selected_pilot].avatar,
)
rocket = Rocket(pilot)

sidebar = BuildSidebar(
    pilot,
    list(PART_CATALOG.values()),
    assets,
    SCREEN_HEIGHT,
)
build_area = BuildArea(
    anchor_pos=(
        sidebar.width + (SCREEN_WIDTH - sidebar.width) / 2,
        SCREEN_HEIGHT - slot_height // 2 - 24,
    ),
    slot_height=slot_height,
    slot_count=slot_count,
    horizontal_snap_points=horizontal_snap_points,
    enable_snap_draws=enable_snap_draws,
)

flight_parts = []
V = 0
W = 0
UP = 0
camera_scroll_y = 0
_background_cache = {}
_background_slices = []


def _load_background_slices():
    pattern = re.compile(r"Background_Slice_(\d+)\.png$")
    numbered = []
    for path in glob.glob("Sprites/Background_Slice_*.png"):
        match = pattern.search(path.replace("\\", "/"))
        if match:
            numbered.append((int(match.group(1)), path))
    numbered.sort(key=lambda item: item[0])
    return [_get_background(path) for _, path in numbered]


def _background_stack_height() -> int:
    if not _background_slices:
        return 0
    return len(_background_slices) * _background_slices[0].get_height()


def _max_scroll() -> int:
    return max(0, _background_stack_height() - SCREEN_HEIGHT)


def update_flight(dt: float):
    global V, UP

    has_fuel = rocket.fuel_remaining > 0
    drag_accel = (
        -2e-5 * rocket.velocity ** 2 * rocket.total_drag
        if rocket.velocity > 0
        else 0.0
    )
    thrust_accel = (
        rocket.total_thrust / rocket.mass
        if has_fuel and rocket.mass > 0
        else 0.0
    )
    rocket.acceleration = drag_accel + thrust_accel - 9.81



    rocket.velocity += rocket.acceleration * dt
    height_delta = rocket.velocity * dt
    rocket.height = max(0.0, rocket.height + height_delta)

    for instance in flight_parts:
        instance.y -= height_delta
        if rocket.velocity < 0:
            if instance.FALL_X == 0:
                instance.FALL_X = rng.random() - 0.5
            instance.x += instance.FALL_X

    if has_fuel:
        rocket.fuel_remaining = max(
            0.0,
            rocket.fuel_remaining - rocket.fuel_consumption_rate * dt,
        )
        rocket.heat += rocket.total_thrust * 0.01 * dt

    rocket.heat = max(0.0, rocket.heat - rocket.total_heat_dissipation * dt)

    V = rocket.velocity
    UP = rocket.velocity


def start_flight():
    global phase, V, W, camera_scroll_y
    errors = rocket.validate()
    if errors:
        print("Launching anyway with issues:", errors)
    print(
        f"Launch! thrust={rocket.total_thrust:.0f} weight={rocket.total_weight:.0f} "
        f"stability={rocket.stability:.1f} fuel={rocket.total_fuel_capacity:.0f} "
        f"fuel_consumption={rocket.total_fuel_consumption:.2f}"
    )
    phase = Phase.FLIGHT
    flight_parts.clear()
    camera_scroll_y = 0
    V = 0
    W = 0
    rocket.height = 0.0
    rocket.heat = 0.0
    rocket.velocity = 0.0
    rocket.fuel_remaining = rocket.total_fuel_capacity
    for instance in build_scene.rocket.parts:
        pos = build_scene.build_area.slot_screen_pos(instance.slot_index, instance.offset_x)
        flight_parts.append(InstanceWrapper(instance, pos))
        W += instance.part_def.weight


build_scene = BuildScene(
    rocket=rocket,
    sidebar=sidebar,
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


def handle_background(scroll_y: float = 0):
    if not _background_slices:
        return

    slice_height = _background_slices[0].get_height()
    slice_width = _background_slices[0].get_width()
    scroll_offset = min(max(0, int(scroll_y)), _max_scroll())
    stack_bottom = SCREEN_HEIGHT + scroll_offset

    for index, slice_image in enumerate(_background_slices):
        y = stack_bottom - (index + 1) * slice_height
        if y + slice_height < 0 or y > SCREEN_HEIGHT:
            continue
        # Tile by image width so halves meet with no gap (SCREEN_WIDTH/2
        # left a seam once the window became larger than 2x slice width).
        for x in range(0, SCREEN_WIDTH, slice_width):
            screen.blit(slice_image, (x, y))


def handle_camera():
    global camera_scroll_y

    if phase == Phase.FLIGHT:
        if not flight_parts:
            return
        center_y = sum(part.y for part in flight_parts) / len(flight_parts)
        if center_y < SCREEN_HEIGHT / 2 - half_camera_boundry and rocket.velocity > 0:
            scroll = max(0.0, rocket.velocity - camera_scroll_speed) * dt
            for part in flight_parts:
                part.y += scroll
            camera_scroll_y = min(camera_scroll_y + scroll, _max_scroll())
        elif rocket.velocity < 0:
            scroll = min(0.0, rocket.velocity + camera_scroll_speed) * dt
            for part in flight_parts:
                part.y -= scroll
            camera_scroll_y = min(camera_scroll_y - scroll, _max_scroll())
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

    screen.fill(BG_COLOR)

    if phase == Phase.BUILD:
        handle_background()
        build_scene.update(dt)
        build_scene.draw(screen)

    elif phase == Phase.FLIGHT:
        # Velocity updated moved to its own function above in this file
        update_flight(dt)
        handle_camera()
        handle_background(camera_scroll_y)
        for instance in flight_parts:
            image = build_scene.assets.get_image(instance.instance.part_def.sprite)
            screen.blit(image, image.get_rect(center=instance.get_pos()))
        sidebar.draw(screen)

    if exit_button.update() == "Pressed":
        return False
    exit_button.render(screen)

    if show_rocket_debug:
        rocket_debug_panel.draw(screen, rocket, in_flight=phase == Phase.FLIGHT)

    pygame.display.flip()
    dt = clock.tick(FPS) / 1000
    return True


if __name__ == "__main__":
    _background_slices.extend(_load_background_slices())
    running = True
    while running:
        running = frame()

    pygame.quit()
