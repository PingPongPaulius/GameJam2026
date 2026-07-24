import pygame

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
        thrusting = phase.name == "FLIGHT" and rocket.fuel_remaining > 0 and rocket.total_thrust > 0
        self._set_loop("engine", thrusting)
        fast = abs(rocket.velocity) > 50  # tune threshold
        self._set_loop("wind", phase.name == "FLIGHT" and fast)
        # edge-triggered one-shots
        if self._prev.get("had_fuel") and rocket.fuel_remaining <= 0:
            #self.play("fuel_empty")
            pass
        self._prev["had_fuel"] = rocket.fuel_remaining > 0
    def _set_loop(self, name: str, active: bool):
        ch = self._channels[name]
        if active and not ch.get_busy():
            ch.play(self._sounds[name], loops=-1)
        elif not active and ch.get_busy():
            ch.fadeout(200)