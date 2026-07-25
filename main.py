import math
import glob
import re
import random as rng
from typing import Optional
from enums.phases import Phase

import asyncio
import pygame

from Tokens.token import Token, Player, Platform
from UI import Button
from anime import Animation

from rocket.part_data import (
    PART_CATALOG,
    load_part_catalog_from_file,
    parse_part_catalog,
    set_part_catalog,
)
from rocket.pilot import Pilot, PilotAttributes, default_mission, mission_alien, mission_human, mission_robot
from rocket.pilot_data import (
    PILOT_CATALOG,
    load_pilots_from_file,
    parse_pilots,
    set_pilot_catalog,
)
from rocket.rocket import Rocket
from rocket.build_area import BuildArea
from api.catalog_client import fetch_parts, fetch_pilots
from api.highscore_client import submit_highscore
from ui.build_sidebar import BuildSidebar
from ui.rocket_debug_panel import RocketDebugPanel
from ui.score_overlay import ScoreOverlay
from ui.slide_cover import SlideCover
from scenes.build_scene import BuildScene, SIDE_MOUNT_TYPES
from scenes.main_menu_scene import MainMenuScene
from rendering.rocket_renderer import draw_rocket
from vector import Vector
from manager.audio_manager import AudioManager
from manager.explosion_manager import ExplosionManager
from rocket.behaviors import check_flight_failure
from rocket.part_types import PartType

from helpers.animation_asset_adapter import AnimationAssetAdapter
from helpers.instance_wrapper import InstanceWrapper

pygame.init()
audio_manager = AudioManager()
explosion_manager = ExplosionManager()
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 1000
BG_COLOR = (20, 20, 20)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
FPS = 60
dt = 1/FPS

phase = Phase.MENU

tokens = []

camera_scroll_speed = 1
half_camera_boundry = 200

loader = Animation()

# Variables for the build area and the rocket
slot_height = 64
slot_count = 20
horizontal_snap_points = 8

# Countdown for the launch
build_countdown_seconds = 20
elapsed = 0.0
_locked = False

# Debug options
show_rocket_debug = True
enable_snap_draws = False

assets = AnimationAssetAdapter()
missions = {0: default_mission, 1: mission_alien, 2: mission_human, 3: mission_robot}

catalogs_ready = False
pilots = PILOT_CATALOG
selected_pilot = 1
pilot = None
rocket = None
sidebar = None
build_area = None
build_scene = None

flight_parts = []
V = 0
W = 0
UP = 0
camera_scroll_y = 0
camera_scroll_x = 0.0
rocket_center_x = 0.0
rocket_center_y = 0.0
max_height = 0.0
max_speed = 0.0
SCORE_SUBMIT_DELAY = 3.0
EXPLOSION_SCORE_DELAY = 1.2
score_submit_timer = 0.0
score_submit_armed = False
rocket_destroyed = False
_background_cache = {}
_background_slices = []


def _flight_rocket_payload() -> dict | None:
    """Pick one part id per required slot from the flown rocket."""
    slot_types = {
        "nose_cone_id": PartType.NOSE_CONE,
        "fuel_tank_id": PartType.FUEL_TANK,
        "engine_id": PartType.ENGINE,
        "fin_id": PartType.FIN,
    }
    by_type = {}
    source_parts = rocket.parts if rocket is not None else []
    for part in source_parts:
        part_type = part.part_def.part_type
        if part_type in slot_types.values() and part_type not in by_type:
            by_type[part_type] = part.part_def.id

    rocket_payload = {}
    for key, part_type in slot_types.items():
        part_id = by_type.get(part_type)
        if not part_id:
            return None
        rocket_payload[key] = part_id
    return rocket_payload


async def on_score_submit(name: str, height: float, top_speed: float):
    rocket_payload = _flight_rocket_payload()
    if rocket_payload is None:
        message = "Rocket needs a nose cone, fuel tank, engine, and fins to submit"
        print(f"Highscore API: ok=False ({message})")
        return False, message

    ok, message = await submit_highscore(
        name,
        height,
        pilot_id=selected_pilot,
        rocket=rocket_payload,
        top_speed=top_speed,
    )
    print(
        f"Highscore API: ok={ok} name={name!r} height={height:.0f} "
        f"top_speed={top_speed:.1f} pilot_id={selected_pilot} "
        f"rocket={rocket_payload} ({message})"
    )
    return ok, message


def set_phase(new_phase):
    global phase
    phase = new_phase

score_overlay = ScoreOverlay(on_submit=on_score_submit)  # on_restart set after build_scene


def _load_background_slices():
    pattern = re.compile(r"Background_Slice_(\d+)\.png$")
    numbered = []
    for path in glob.glob("Sprites/Background_Slice_*.png"):
        match = pattern.search(path.replace("\\", "/"))
        if match:
            numbered.append((int(match.group(1)), path))
    numbered.sort(key=lambda item: item[0])
    return [_get_background(path) for _, path in numbered]


def rotated_offset(dx: float, dy: float, angle: float) -> tuple:
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    return dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a


def _show_score_overlay():
    global phase, score_submit_timer, score_submit_armed
    score_submit_timer = 0.0
    score_submit_armed = False
    phase = Phase.RESULTS
    score_overlay.show(max_height, max_speed)


def _trigger_explosion(failure):
    global rocket_destroyed, score_submit_timer, score_submit_armed
    if rocket_destroyed:
        return
    rocket_destroyed = True
    score_submit_armed = True
    score_submit_timer = 0.0
    rocket.y_velocity = 0.0
    rocket.x_velocity = 0.0
    rocket.velocity = 0.0
    rocket.rotation_speed = 0.0
    rocket.fuel_remaining = 0.0  # stops engine loop during the boom
    explosion_manager.spawn(rocket_center_x, rocket_center_y, failure.severity)
    audio_manager.play("explosion")
    print(f"Rocket destroyed: {failure.kind} (severity={failure.severity:.2f})")


def update_flight(dt: float):
    global V, UP, rocket_center_x, rocket_center_y, max_height, max_speed, phase 
    global score_submit_timer, score_submit_armed, rocket_destroyed



    DRAG_COEFFICIENT = 2e-5 * 30
    THRUST_COEFFICIENT = 10


    # After an explosion, wait briefly so the VFX can play, then score.
    if rocket_destroyed:
        score_submit_timer += dt
        if score_submit_timer >= EXPLOSION_SCORE_DELAY:
            _show_score_overlay()
        return

    
    has_fuel = rocket.fuel_remaining > 0
    y_drag_accel = (
        -DRAG_COEFFICIENT * rocket.y_velocity * abs(rocket.y_velocity) * rocket.total_drag
    )
    y_thrust_accel = (
        (THRUST_COEFFICIENT * rocket.total_thrust * math.cos(rocket.rotation)) / rocket.mass
        if has_fuel and rocket.mass > 0
        else 0.0
    )
    x_drag_accel = (
        -DRAG_COEFFICIENT * rocket.x_velocity * abs(rocket.x_velocity) * rocket.total_drag
    )
    x_thrust_accel = (
        (THRUST_COEFFICIENT * rocket.total_thrust * math.sin(rocket.rotation)) / rocket.mass
        if has_fuel and rocket.mass > 0
        else 0.0
    )

    thrust_torque_accel = (
        (rocket.center_of_gravity_x - rocket.center_of_thrust_x) * rocket.total_thrust / rocket.moment_of_inertia
        if has_fuel and rocket.moment_of_inertia > 0
        else 0.0
    )

    FIN_DAMPING_COEFFICIENT = 0.02
    rocket.rotation_damping = (
        FIN_DAMPING_COEFFICIENT * rocket.stability * rocket.velocity / rocket.moment_of_inertia
        if rocket.moment_of_inertia > 0
        else 0.0
    )

    # Thrust vectoring: each gimbal-capable engine swivels its nozzle to fight the
    # rocket's current tilt (sin of rotation, wraps naturally through upside-down)
    # and spin rate, like a small PD autopilot per engine. The resulting torque is
    # weighted by that engine's own distance from the center of gravity, since an
    # engine further from the COG gets more leverage out of the same deflection.
    GIMBAL_KP = 0.6
    GIMBAL_KD = 0.8
    MAX_GIMBAL_ANGLE = math.radians(20)
    GIMBAL_SLEW_RATE = math.radians(180)

    target_gimbal_angle = (
        max(
            -MAX_GIMBAL_ANGLE,
            min(MAX_GIMBAL_ANGLE, -(GIMBAL_KP * math.sin(rocket.rotation) + GIMBAL_KD * rocket.rotation_speed)),
        )
        if has_fuel
        else 0.0
    )

    cog_y = rocket.center_of_gravity_y
    gimbal_torque = 0.0
    for p in rocket.parts:
        if not p.part_def.gimbal:
            continue
        max_step = GIMBAL_SLEW_RATE * dt
        angle_delta = max(-max_step, min(max_step, target_gimbal_angle - p.gimbal_angle))
        p.gimbal_angle += angle_delta
        if has_fuel and rocket.moment_of_inertia > 0:
            engine_dy = abs((p.slot_index * 64.0 / Rocket.VERTICAL_UNIT) - cog_y)
            gimbal_torque += p.part_def.thrust * engine_dy * math.sin(p.gimbal_angle)

    gimbal_torque_accel = gimbal_torque / rocket.moment_of_inertia if rocket.moment_of_inertia > 0 else 0.0

    rocket.rotation_acceleration = (
        thrust_torque_accel - rocket.rotation_damping * rocket.rotation_speed + gimbal_torque_accel
    )

    rocket.rotation_speed += rocket.rotation_acceleration * dt
    rocket.rotation += rocket.rotation_speed * dt
    
    rocket.y_acceleration = y_drag_accel + y_thrust_accel - 9.81
    rocket.x_acceleration = x_drag_accel + x_thrust_accel

    rocket.acceleration = math.sqrt(rocket.x_acceleration ** 2 + rocket.y_acceleration ** 2)
    rocket.velocity = math.sqrt(rocket.x_velocity ** 2 + rocket.y_velocity ** 2)

    rocket.COM_x = rocket.center_of_gravity_x
    rocket.COT_x = rocket.center_of_thrust_x
    rocket.rotation_inertia = rocket.moment_of_inertia

    land_hit = rocket.height <= 0 and rocket.y_velocity < 0
    impact_speed = abs(rocket.y_velocity) if land_hit else 0.0

    rocket.y_velocity += rocket.y_acceleration * dt if not land_hit else 0
    rocket.x_velocity += rocket.x_acceleration * dt if not land_hit else 0

    previous_height = rocket.height
    height_delta = rocket.y_velocity * dt
    rocket.height = max(0.0, rocket.height + height_delta)

    max_height = max(max_height, rocket.height)
    max_speed = max(max_speed, rocket.velocity)
    x_delta = rocket.x_velocity * dt if not land_hit else 0.0
    rocket.x_position += x_delta

    rocket_center_y -= height_delta
    rocket_center_x += x_delta

    if has_fuel:
        rocket.fuel_remaining = max(
            0.0,
            rocket.fuel_remaining - rocket.fuel_consumption_rate * dt,
        )
        rocket.heat += rocket.total_thrust * 0.01 * dt

    rocket.heat = max(0.0, rocket.heat - rocket.total_heat_dissipation * dt)

    V = rocket.y_velocity
    UP = rocket.y_velocity

    landed = previous_height > 1.0 and rocket.height <= 0.0
    explode = True
    for part in flight_parts:
        if part.instance.part_def.part_type == PartType.FIN:
            explode = False
    failure = check_flight_failure(
        rocket,
        landed=landed,
        impact_speed=impact_speed,
        force_failure=explode,
    )
    if failure:
        _trigger_explosion(failure)
        return

    # Soft touchdown — no boom, go straight to score.
    if landed:
        rocket.y_velocity = 0.0
        rocket.x_velocity = 0.0
        rocket.velocity = 0.0
        _show_score_overlay()
        return

    # 3s after the rocket starts falling, open score submit.
    if (
        not score_submit_armed
        and max_height > 1.0
        and rocket.y_velocity < 0.0
    ):
        score_submit_armed = True
        score_submit_timer = 0.0

    if score_submit_armed:
        score_submit_timer += dt
        if score_submit_timer >= SCORE_SUBMIT_DELAY:
            _show_score_overlay()


def start_flight():
    global phase, V, W, camera_scroll_y, rocket_center_x, rocket_center_y
    global max_height, max_speed, score_submit_timer, score_submit_armed, rocket_destroyed
    errors = rocket.validate()
    if errors:
        print("Launching anyway with issues:", errors)
    print(
        f"Launch! thrust={rocket.total_thrust:.0f} weight={rocket.total_weight:.0f} "
        f"stability={rocket.stability:.1f} fuel={rocket.total_fuel_capacity:.2f} "
        f"fuel_consumption={rocket.fuel_consumption_rate:.3f}"
    )
    phase = Phase.FLIGHT
    flight_parts.clear()
    explosion_manager.clear()
    camera_scroll_y = 0
    camera_scroll_x = 0.0
    max_height = 0.0
    max_speed = 0.0
    score_submit_timer = 0.0
    score_submit_armed = False
    rocket_destroyed = False
    V = 0
    W = 0
    rocket.height = 0.0
    rocket.x_position = 0.0
    rocket.heat = 0.0
    rocket.y_velocity = 0.0
    rocket.x_velocity = 0.0
    rocket.rotation = 0.0
    rocket.rotation_speed = 0.0
    rocket.fuel_remaining = rocket.total_fuel_capacity
    rocket.rotation_acceleration = 0.0
    rocket.drag_reduction_factor = rocket.min_drag_reduction_factor
    parts_used = set()
    is_robot_part_used = False
    for instance in build_scene.rocket.parts:
        instance.gimbal_angle = 0.0
        pos = build_scene.build_area.slot_screen_pos(instance.slot_index, instance.offset_x)
        flight_parts.append(InstanceWrapper(instance, pos))
        W += instance.part_def.weight
        parts_used.add(instance.part_def.name)
        print(instance.part_def.name)
        if "Nose" in instance.part_def.name:
            is_robot_part_used = True
    
    data = {'time': build_scene.last_placed, 'parts': len(parts_used), 'battery': is_robot_part_used}
    rocket.apply_pilot_effects(data)

    total_weight = sum(instance.instance.part_def.weight for instance in flight_parts)
    if total_weight > 0:
        pivot_x = sum(instance.x * instance.instance.part_def.weight for instance in flight_parts) / total_weight
        pivot_y = sum(instance.y * instance.instance.part_def.weight for instance in flight_parts) / total_weight
    elif flight_parts:
        pivot_x = sum(instance.x for instance in flight_parts) / len(flight_parts)
        pivot_y = sum(instance.y for instance in flight_parts) / len(flight_parts)
    else:
        pivot_x = pivot_y = 0.0

    rocket_center_x = pivot_x
    rocket_center_y = pivot_y
    for instance in flight_parts:
        instance.local_dx = instance.x - pivot_x
        instance.local_dy = instance.y - pivot_y

def catalogs_are_ready() -> bool:
    return catalogs_ready


main_menu_scene = MainMenuScene(
    screen,
    on_phase_change=set_phase,
    can_start=catalogs_are_ready,
)
rocket_debug_panel = RocketDebugPanel()


def _pick_pilot_id():
    if not PILOT_CATALOG:
        raise RuntimeError("No pilots loaded")
    if rng.randint(1, 100) > 99 and 4 in PILOT_CATALOG:
        return 4
    choices = [pid for pid in PILOT_CATALOG if pid != 4]
    if choices:
        return rng.choice(choices)
    return next(iter(PILOT_CATALOG))


def apply_catalogs_to_game():
    """Rebuild pilot/rocket/sidebar/build scene from the current catalogs."""
    global pilots, selected_pilot, pilot, rocket, sidebar, build_area, build_scene

    pilots = PILOT_CATALOG
    selected_pilot = _pick_pilot_id()
    pilot_def = pilots[selected_pilot]
    pilot = Pilot(
        name=pilot_def.name,
        attributes=PilotAttributes(**pilot_def.attributes),
        portrait_sprite=pilot_def.avatar,
        mission=missions.get(pilot_def.mission, default_mission),
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
    if build_scene is None:
        build_scene = BuildScene(
            rocket=rocket,
            sidebar=sidebar,
            build_area=build_area,
            assets=assets,
            countdown_seconds=build_countdown_seconds,
            on_timeout=start_flight,
        )
    else:
        build_scene.rocket = rocket
        build_scene.sidebar = sidebar
        build_scene.build_area = build_area
        build_scene.reset(build_countdown_seconds)


def load_catalogs_from_files() -> tuple[bool, str]:
    """Load parts + pilots from bundled JSON files."""
    try:
        parts = load_part_catalog_from_file()
        pilots = load_pilots_from_file()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return False, f"Local catalog files: {exc}"

    if not parts or not pilots:
        return False, "Local catalog files were empty"

    set_part_catalog(parts)
    set_pilot_catalog(pilots)
    return True, f"Loaded offline {len(parts)} parts, {len(pilots)} pilots"


async def load_catalogs() -> tuple[bool, str]:
    """Fetch parts + pilots from the API, falling back to local JSON if needed."""
    global catalogs_ready

    parts_ok, parts_result = await fetch_parts()
    pilots_ok, pilots_result = await fetch_pilots()
    if parts_ok and pilots_ok:
        set_part_catalog(parse_part_catalog(parts_result))
        set_pilot_catalog(parse_pilots(pilots_result))
        if PART_CATALOG and PILOT_CATALOG:
            apply_catalogs_to_game()
            catalogs_ready = True
            return True, f"Loaded {len(PART_CATALOG)} parts, {len(PILOT_CATALOG)} pilots from API"
        api_error = "API returned empty catalogs"
    else:
        reasons = []
        if not parts_ok:
            reasons.append(f"parts: {parts_result}")
        if not pilots_ok:
            reasons.append(f"pilots: {pilots_result}")
        api_error = "; ".join(reasons)

    print(f"Catalog API unavailable ({api_error}); trying local JSON fallback")
    ok, message = load_catalogs_from_files()
    if not ok:
        catalogs_ready = False
        return False, f"{api_error}; {message}"

    apply_catalogs_to_game()
    catalogs_ready = True
    return True, f"{message} (API unavailable: {api_error})"


async def refresh_catalogs_for_menu():
    main_menu_scene.status_text = "Loading parts & pilots..."
    ok, message = await load_catalogs()
    if ok:
        offline = "offline" in message.lower() or "API unavailable" in message
        main_menu_scene.status_text = "Playing offline (local parts/pilots)" if offline else ""
        print(f"Catalogs: {message}")
    else:
        main_menu_scene.status_text = f"Failed to load game data: {message}"
        print(f"Catalog load failed: {message}")


async def restart_game() -> bool:
    """Reload catalogs (API or local fallback), then return to a fresh build phase."""
    global phase, V, W, UP, camera_scroll_y, rocket_center_x, rocket_center_y
    global max_height, max_speed, score_submit_timer, score_submit_armed, rocket_destroyed

    ok, message = await load_catalogs()
    if not ok:
        print(f"Catalog reload failed on restart: {message}")
        return False
    print(f"Catalogs on restart: {message}")

    flight_parts.clear()
    explosion_manager.clear()
    phase = Phase.BUILD
    V = 0
    W = 0
    UP = 0
    camera_scroll_y = 0
    camera_scroll_x = 0.0
    rocket_center_x = 0.0
    rocket_center_y = 0.0
    max_height = 0.0
    max_speed = 0.0
    score_submit_timer = 0.0
    score_submit_armed = False
    rocket_destroyed = False
    return True


score_overlay.on_restart = restart_game

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


def update_flight_part_positions():
    for instance in flight_parts:
        rot_dx, rot_dy = rotated_offset(instance.local_dx, instance.local_dy, rocket.rotation)
        instance.x = rocket_center_x + rot_dx
        instance.y = rocket_center_y + rot_dy


def find_player() -> Optional[Player]:
    for token in tokens:
        if isinstance(token, Player):
            return token
    return None

def _get_background(path: str):
    if path not in _background_cache:
        _background_cache[path] = pygame.image.load(path).convert()
    return _background_cache[path]


def handle_background(scroll_y: float = 0, scroll_x: float = 0):
    if not _background_slices:
        return

    slice_height = _background_slices[0].get_height()
    slice_width = _background_slices[0].get_width()
    scroll_offset = max(0, int(scroll_y))
    stack_bottom = SCREEN_HEIGHT + scroll_offset

    # Background moves opposite to sideways rocket movement, giving a
    # parallax feel of the camera panning with the rocket.
    x_offset = int(scroll_x) % slice_width

    # Draw enough vertical tiles to fill the screen. Past the authored stack,
    # keep repeating the topmost slice so flight can go forever.
    start_index = max(0, scroll_offset // slice_height - 1)
    end_index = (SCREEN_HEIGHT + scroll_offset) // slice_height + 1
    top_slice = _background_slices[-1]

    for index in range(start_index, end_index + 1):
        slice_image = (
            _background_slices[index]
            if index < len(_background_slices)
            else top_slice
        )
        y = stack_bottom - (index + 1) * slice_height
        if y + slice_height < 0 or y > SCREEN_HEIGHT:
            continue
        for x in range(-x_offset - slice_width, SCREEN_WIDTH + slice_width, slice_width):
            screen.blit(slice_image, (x, y))


def handle_camera():
    global camera_scroll_y, camera_scroll_x, rocket_center_x, rocket_center_y

    if phase == Phase.FLIGHT:
        if not flight_parts:
            return

        top_bound = SCREEN_HEIGHT / 2 - half_camera_boundry
        left_bound = SCREEN_WIDTH / 2 - half_camera_boundry
        right_bound = SCREEN_WIDTH / 2 + half_camera_boundry

        if rocket_center_y < top_bound and rocket.y_velocity > 0:
            scroll = max(0.0, rocket.y_velocity - camera_scroll_speed) * dt
            rocket_center_y += scroll
            camera_scroll_y += scroll
        elif rocket.y_velocity < 0:
            # Falling: unwind the scroll we built up climbing, capped at what's
            # left to unwind so the rocket free-falls normally once back at
            # ground level (camera_scroll_y == 0).
            excess = min(
                max(0.0, -rocket.y_velocity - camera_scroll_speed) * dt,
                camera_scroll_y,
            )
            rocket_center_y -= excess
            camera_scroll_y -= excess

        if rocket_center_x < left_bound:
            camera_scroll_x -= left_bound - rocket_center_x
            rocket_center_x = left_bound
        elif rocket_center_x > right_bound:
            camera_scroll_x += rocket_center_x - right_bound
            rocket_center_x = right_bound
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


async def frame():
    global dt, phase
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if score_overlay.visible and score_overlay.handle_event(event):
            continue
        if phase == Phase.BUILD and build_scene is not None:
            build_scene.handle_event(event)

    screen.fill(BG_COLOR)
    if phase == Phase.MENU:
        main_menu_scene.update(dt)
        main_menu_scene.draw(screen)
    if phase == Phase.BUILD and build_scene is not None:
        handle_background()
        build_scene.update(dt)
        build_scene.draw(screen)

    elif phase in (Phase.FLIGHT, Phase.RESULTS):
        if phase == Phase.FLIGHT:
            update_flight(dt)
            audio_manager.update_from_rocket(rocket, phase)
            handle_camera()
        explosion_manager.update(dt)
        update_flight_part_positions()
        handle_background(camera_scroll_y)
        if not rocket_destroyed:
            rotation_degrees = -math.degrees(rocket.rotation)
            for instance in flight_parts:
                part = instance.instance
                image = build_scene._part_image(
                    part.part_def,
                    part.offset_x,
                    slot=part.slot_index,
                )
                part_rotation_degrees = rotation_degrees
                if part.part_def.gimbal:
                    part_rotation_degrees += math.degrees(part.gimbal_angle)
                rotated_image = pygame.transform.rotate(image, part_rotation_degrees)
                screen.blit(rotated_image, rotated_image.get_rect(center=instance.get_pos()))
        explosion_manager.draw(screen)
        sidebar.draw(screen)

    if show_rocket_debug and rocket is not None:
        if phase == Phase.BUILD or phase == Phase.FLIGHT:
            rocket_debug_panel.draw(
                screen,
                rocket,
                in_flight=phase in (Phase.FLIGHT, Phase.RESULTS),
                position=(rocket.x_position, rocket.height),
            )

    score_overlay.update(dt)
    score_overlay.draw(screen)

    pygame.display.flip()
    dt = clock.tick(FPS) / 1000
    # Yield to the browser event loop (required for pygbag / python-wasm).
    await asyncio.sleep(0)
    return True


async def main():
    _background_slices.extend(_load_background_slices())
    asyncio.create_task(refresh_catalogs_for_menu())
    running = True
    while running:
        running = await frame()


if __name__ == "__main__":
    asyncio.run(main())
