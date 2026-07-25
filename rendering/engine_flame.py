import math

import pygame

from anime import Animation
from rocket.part_types import PartType

FLAME_SHEET = "Sprites/Animations/Animation_Flame_Frame_100x100.png"
FRAME_SIZE = 100
DISPLAY_SIZE = (48, 48)
# Part sprites are 64x64 and centered; place flame below the nozzle with a slight tuck.
NOZZLE_OFFSET_Y = 32 + DISPLAY_SIZE[1] // 3
# Vector engine has twin nozzles (from Engine_Vector.png bottom clusters, scaled to 64px).
VECTOR_ENGINE_ID = "vector_engine"
VECTOR_NOZZLE_OFFSET_X = 20


class EngineFlameAnimator:
    def __init__(self, display_size=DISPLAY_SIZE, frame_speed=0.07):
        animation = Animation()
        animation.add(
            "flame",
            FLAME_SHEET,
            FRAME_SIZE,
            FRAME_SIZE,
            speed=frame_speed,
        )
        frames = [
            pygame.transform.smoothscale(frame, display_size)
            for frame in animation.animations["flame"].anime
        ]
        animation.animations["flame"].anime = frames
        self._animation = animation

    def step(self, dt: float):
        self._animation.step(dt)

    def _flame_offsets(self, part_def) -> list[tuple[float, float]]:
        if part_def.id == VECTOR_ENGINE_ID:
            return [
                (-VECTOR_NOZZLE_OFFSET_X, NOZZLE_OFFSET_Y),
                (VECTOR_NOZZLE_OFFSET_X, NOZZLE_OFFSET_Y),
            ]
        return [(0.0, NOZZLE_OFFSET_Y)]

    def draw(
        self,
        surface,
        flight_parts,
        rocket_rotation: float,
        thrusting: bool,
        rotated_offset,
    ):
        if not thrusting:
            return

        frame = self._animation.curr_frame()
        for wrapper in flight_parts:
            part = wrapper.instance
            if part.part_def.part_type != PartType.ENGINE:
                continue

            # Match part drawing: pygame degrees are -rocket, with +gimbal on top.
            sprite_degrees = -math.degrees(rocket_rotation)
            offset_angle = rocket_rotation
            if part.part_def.gimbal:
                sprite_degrees += math.degrees(part.gimbal_angle)
                offset_angle += part.gimbal_angle

            rotated = pygame.transform.rotate(frame, sprite_degrees)
            for local_x, local_y in self._flame_offsets(part.part_def):
                fx, fy = rotated_offset(local_x, local_y, offset_angle)
                pos = (wrapper.x + fx, wrapper.y + fy)
                surface.blit(rotated, rotated.get_rect(center=pos))
