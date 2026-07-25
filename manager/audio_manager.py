import sys
import pygame

# Wind is silent at/below MIN, full volume at/above MAX. Tune to feel.
WIND_MIN_SPEED = 20.0
WIND_MAX_SPEED = 200.0
WIND_VOLUME = 0.7
# No wind audio above this altitude (atmosphere thins out).
WIND_MAX_HEIGHT = 7000.0
EXPLOSION_VOLUME = 0.85

# Pygbag / python-wasm needs OGG; desktop keeps MP3.
AUDIO_EXT = "ogg" if sys.platform == "emscripten" else "mp3"


class AudioManager:
    def __init__(self):
        pygame.mixer.init()

        # Add sounds effects
        self._sounds = {
            #"part_place": pygame.mixer.Sound("Sounds/part_place.ogg"),
            "engine": pygame.mixer.Sound(f"audio/rocket-boost.{AUDIO_EXT}"),
            "wind": pygame.mixer.Sound(f"audio/wind.{AUDIO_EXT}"),
            "explosion": pygame.mixer.Sound(f"audio/explosion.{AUDIO_EXT}"),
            "metal_shutter": pygame.mixer.Sound(f"audio/metal-shutter.{AUDIO_EXT}"),
        }

        # Set volume for sounds effects
        self._sounds["wind"].set_volume(WIND_VOLUME)
        self._sounds["explosion"].set_volume(EXPLOSION_VOLUME)

        # Loops on 0/1; one-shots on 2 so engine/wind fadeouts never cut them off.
        self._channels = {
            "engine": pygame.mixer.Channel(0),
            "wind": pygame.mixer.Channel(1),
            "sfx": pygame.mixer.Channel(2),
        }
        self._prev = {}

    def play(self, name: str):
        snd = self._sounds.get(name)
        if snd:
            self._channels["sfx"].play(snd)

    def update_from_rocket(self, rocket, phase):
        in_flight = phase.name == "FLIGHT"
        thrusting = in_flight and rocket.fuel_remaining > 0 and rocket.total_thrust > 0
        self._set_loop("engine", thrusting, 0.2)

        wind_volume = (
            self._wind_volume(rocket.velocity, rocket.height) if in_flight else 0.0
        )
        self._set_loop("wind", wind_volume > 0.01, volume=wind_volume)

        # edge-triggered one-shots
        if self._prev.get("had_fuel") and rocket.fuel_remaining <= 0:
            #self.play("fuel_empty")
            pass
        self._prev["had_fuel"] = rocket.fuel_remaining > 0

    def _wind_volume(self, speed: float, height: float) -> float:
        if height > WIND_MAX_HEIGHT:
            return 0.0
        speed = abs(speed)
        if speed <= WIND_MIN_SPEED:
            return 0.0
        if speed >= WIND_MAX_SPEED:
            return 1.0
        return (speed - WIND_MIN_SPEED) / (WIND_MAX_SPEED - WIND_MIN_SPEED)

    def _set_loop(self, name: str, active: bool, volume: float = 1.0):
        ch = self._channels[name]
        if active:
            if not ch.get_busy():
                ch.play(self._sounds[name], loops=-1)
            ch.set_volume(max(0.0, min(1.0, volume)))
        elif ch.get_busy():
            ch.fadeout(200)
