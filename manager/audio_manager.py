import pygame

# Wind is silent at/below MIN, full volume at/above MAX. Tune to feel.
WIND_MIN_SPEED = 20.0
WIND_MAX_SPEED = 200.0


class AudioManager:
    def __init__(self):
        pygame.mixer.init()
        self._sounds = {
            #"part_place": pygame.mixer.Sound("Sounds/part_place.ogg"),
            "engine": pygame.mixer.Sound("audio/rocket-boost.mp3"),
            "wind": pygame.mixer.Sound("audio/wind.mp3"),
        }
        self._channels = {
            "engine": pygame.mixer.Channel(0),
            "wind": pygame.mixer.Channel(1),
        }
        self._prev = {}

    def play(self, name: str):
        snd = self._sounds.get(name)
        if snd:
            snd.play()  # one-shot; mixes with whatever is already playing

    def update_from_rocket(self, rocket, phase):
        in_flight = phase.name == "FLIGHT"
        thrusting = in_flight and rocket.fuel_remaining > 0 and rocket.total_thrust > 0
        self._set_loop("engine", thrusting)

        wind_volume = self._wind_volume(rocket.velocity) if in_flight else 0.0
        self._set_loop("wind", wind_volume > 0.01, volume=wind_volume)

        # edge-triggered one-shots
        if self._prev.get("had_fuel") and rocket.fuel_remaining <= 0:
            #self.play("fuel_empty")
            pass
        self._prev["had_fuel"] = rocket.fuel_remaining > 0

    def _wind_volume(self, speed: float) -> float:
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
