import math
import random

import pygame

from anime import Animation

EXPLOSION_SHEET = "Sprites/Animations/Animation_Explosion_Frame_300x300.png"
FRAME_SIZE = 300
FRAME_DURATION = 0.08
# Base on-screen size at severity 1.0 (sheet frames are 300x300).
BASE_DISPLAY_SIZE = 180


class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "radius", "color")

    def __init__(self, x, y, vx, vy, life, radius, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.radius = radius
        self.color = color


class _ParticleExplosion:
    """Legacy procedural particle burst. Kept for reference / easy switch-back."""

    def __init__(self, x: float, y: float, severity: float = 1.0):
        self.x = x
        self.y = y
        self.severity = max(0.4, severity)
        self.age = 0.0
        self.duration = 0.7 + 0.25 * self.severity
        self.particles: list[_Particle] = []
        self._spawn_particles()

    def _spawn_particles(self):
        count = int(28 * self.severity)
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(80, 280) * self.severity
            life = random.uniform(0.25, self.duration)
            radius = random.uniform(3, 10) * self.severity
            # Orange / yellow / white core mix
            palette = (
                (255, 220, 120),
                (255, 160, 60),
                (240, 90, 40),
                (200, 60, 40),
            )
            color = random.choice(palette)
            self.particles.append(
                _Particle(
                    self.x,
                    self.y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    life,
                    radius,
                    color,
                )
            )

    def update(self, dt: float) -> bool:
        """Advance the explosion. Returns False when finished."""
        self.age += dt
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vx *= 0.92
            p.vy *= 0.92
            p.vy += 40 * dt  # slight gravity so debris falls
            alive.append(p)
        self.particles = alive
        return self.age < self.duration and bool(self.particles)

    def draw(self, surface: pygame.Surface):
        # Expanding flash ring
        if self.age < 0.2:
            t = self.age / 0.2
            radius = int(20 + 90 * self.severity * t)
            alpha = int(180 * (1.0 - t))
            flash = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash, (255, 240, 180, alpha), (radius, radius), radius)
            surface.blit(flash, (int(self.x - radius), int(self.y - radius)))

        for p in self.particles:
            fade = max(0.0, p.life / p.max_life)
            r = max(1, int(p.radius * fade))
            color = tuple(int(c * fade) for c in p.color)
            pygame.draw.circle(surface, color, (int(p.x), int(p.y)), r)


class _Explosion:
    """Spritesheet explosion using Animation_Explosion_Frame_300x300."""

    def __init__(
        self,
        x: float,
        y: float,
        frames: list[pygame.Surface],
        severity: float = 1.0,
        frame_duration: float = FRAME_DURATION,
    ):
        self.x = x
        self.y = y
        self.severity = max(0.4, severity)
        self._frames = frames
        self._frame_duration = frame_duration
        self._frame_index = 0
        self._timer = 0.0
        size = max(48, int(BASE_DISPLAY_SIZE * self.severity))
        self._scaled = [
            pygame.transform.smoothscale(frame, (size, size)) for frame in frames
        ]

    def update(self, dt: float) -> bool:
        """Advance the explosion. Returns False when finished."""
        self._timer += dt
        while self._timer >= self._frame_duration:
            self._timer -= self._frame_duration
            self._frame_index += 1
            if self._frame_index >= len(self._scaled):
                return False
        return True

    def draw(self, surface: pygame.Surface):
        frame = self._scaled[self._frame_index]
        surface.blit(frame, frame.get_rect(center=(int(self.x), int(self.y))))


class ExplosionManager:
    def __init__(self):
        self._explosions: list[_Explosion] = []
        self._frames: list[pygame.Surface] | None = None

    def _ensure_frames(self) -> list[pygame.Surface]:
        # Loaded lazily: convert_alpha needs a display mode, and main creates
        # this manager before set_mode.
        if self._frames is None:
            animation = Animation()
            animation.add(
                "explosion",
                EXPLOSION_SHEET,
                FRAME_SIZE,
                FRAME_SIZE,
                speed=FRAME_DURATION,
            )
            self._frames = animation.animations["explosion"].anime
        return self._frames

    def spawn(self, x: float, y: float, severity: float = 1.0) -> None:
        frames = self._ensure_frames()
        self._explosions.append(_Explosion(x, y, frames, severity))

    def update(self, dt: float) -> None:
        self._explosions = [e for e in self._explosions if e.update(dt)]

    def draw(self, surface: pygame.Surface) -> None:
        for explosion in self._explosions:
            explosion.draw(surface)

    def active(self) -> bool:
        return bool(self._explosions)

    def clear(self) -> None:
        self._explosions.clear()
