import os
import sys
import pygame

# Wind is silent at/below MIN, full volume at/above MAX. Tune to feel.
WIND_MIN_SPEED = 20.0
WIND_MAX_SPEED = 200.0
WIND_VOLUME = 0.7
# No wind audio above this altitude (atmosphere thins out).
WIND_MAX_HEIGHT = 7000.0
EXPLOSION_VOLUME = 0.85
MILESTONE_HEIGHT = 100_000.0

# Pygbag / python-wasm needs OGG; desktop keeps MP3.
AUDIO_EXT = "ogg" if sys.platform == "emscripten" else "mp3"

VOLUME_CHANNELS = ("music", "sfx", "engine", "wind")


def _audio_path(stem: str) -> str:
    """Prefer platform extension; fall back to the other if missing."""
    preferred = f"audio/{stem}.{AUDIO_EXT}"
    if os.path.exists(preferred):
        return preferred
    other = "mp3" if AUDIO_EXT == "ogg" else "ogg"
    fallback = f"audio/{stem}.{other}"
    if os.path.exists(fallback):
        return fallback
    return preferred


class AudioManager:
    def __init__(self):
        pygame.mixer.init()

        self._volumes = {name: 1.0 for name in VOLUME_CHANNELS}

        self._sounds = {
            #"part_place": pygame.mixer.Sound("Sounds/part_place.ogg"),
            "engine": pygame.mixer.Sound(_audio_path("rocket-boost")),
            "wind": pygame.mixer.Sound(_audio_path("wind")),
            "explosion": pygame.mixer.Sound(_audio_path("explosion")),
            "metal_shutter": pygame.mixer.Sound(_audio_path("metal-shutter")),
        }

        # Per-sound base levels for one-shots (scaled by the SFX slider).
        self._sfx_base_volumes = {
            "explosion": EXPLOSION_VOLUME,
        }
        self._sounds["wind"].set_volume(WIND_VOLUME)
        self._sounds["explosion"].set_volume(EXPLOSION_VOLUME)

        # Loops on 0/1; one-shots on 2 so engine/wind fadeouts never cut them off.
        self._channels = {
            "engine": pygame.mixer.Channel(0),
            "wind": pygame.mixer.Channel(1),
            "sfx": pygame.mixer.Channel(2),
        }
        self._prev = {}
        self._music_mode = None  # None | "menu" | "milestone"
        self._milestone_played = False
        self._soundtrack_path = _audio_path("soundtrack")

    def get_volume(self, name: str) -> float:
        return self._volumes.get(name, 1.0)

    def set_volume(self, name: str, value: float):
        if name not in self._volumes:
            return
        self._volumes[name] = max(0.0, min(1.0, value))
        self._apply_volumes()

    def play(self, name: str):
        snd = self._sounds.get(name)
        if not snd:
            return
        base = self._sfx_base_volumes.get(name, 1.0)
        snd.set_volume(base * self._volumes["sfx"])
        self._channels["sfx"].play(snd)

    def play_menu_music(self):
        """Loop soundtrack on the main menu / options screens."""
        if self._music_mode == "menu" and pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(self._volumes["music"])
            return
        try:
            pygame.mixer.music.load(self._soundtrack_path)
            pygame.mixer.music.set_volume(self._volumes["music"])
            pygame.mixer.music.play(loops=-1)
            self._music_mode = "menu"
        except pygame.error as exc:
            print(f"Failed to play menu soundtrack: {exc}")
            self._music_mode = None

    def stop_music(self, fade_ms: int = 300):
        if self._music_mode is None and not pygame.mixer.music.get_busy():
            return
        if fade_ms > 0:
            pygame.mixer.music.fadeout(fade_ms)
        else:
            pygame.mixer.music.stop()
        self._music_mode = None

    def on_flight_start(self):
        """Reset milestone flag and stop menu music for a new flight."""
        self._milestone_played = False
        self.stop_music(fade_ms=200)

    def maybe_play_milestone(self, height: float):
        """Play soundtrack once when the rocket first passes 100 km."""
        if self._milestone_played or height < MILESTONE_HEIGHT:
            return
        self._milestone_played = True
        try:
            pygame.mixer.music.load(self._soundtrack_path)
            pygame.mixer.music.set_volume(self._volumes["music"])
            pygame.mixer.music.play(loops=0)
            self._music_mode = "milestone"
        except pygame.error as exc:
            print(f"Failed to play milestone soundtrack: {exc}")
            self._music_mode = None

    def update_from_rocket(self, rocket, phase):
        in_flight = phase.name == "FLIGHT"
        thrusting = in_flight and rocket.fuel_remaining > 0 and rocket.total_thrust > 0
        self._set_loop("engine", thrusting, 0.2)

        wind_volume = (
            self._wind_volume(rocket.velocity, rocket.height) if in_flight else 0.0
        )
        self._set_loop("wind", wind_volume > 0.01, volume=wind_volume)

        if in_flight:
            self.maybe_play_milestone(rocket.height)

        # edge-triggered one-shots
        if self._prev.get("had_fuel") and rocket.fuel_remaining <= 0:
            #self.play("fuel_empty")
            pass
        self._prev["had_fuel"] = rocket.fuel_remaining > 0

    def _apply_volumes(self):
        pygame.mixer.music.set_volume(self._volumes["music"])

        # Engine/wind channel levels are reapplied each flight frame.
        # Scale idle engine channel immediately so options tweaks are audible.
        engine_ch = self._channels["engine"]
        if engine_ch.get_busy():
            engine_ch.set_volume(self._volumes["engine"])

        for name, base in self._sfx_base_volumes.items():
            snd = self._sounds.get(name)
            if snd is not None:
                snd.set_volume(base * self._volumes["sfx"])

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
        user_vol = self._volumes.get(name, 1.0)
        if active:
            if not ch.get_busy():
                ch.play(self._sounds[name], loops=-1)
            ch.set_volume(max(0.0, min(1.0, volume * user_vol)))
        elif ch.get_busy():
            ch.fadeout(200)
