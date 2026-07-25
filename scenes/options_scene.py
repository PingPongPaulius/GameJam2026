import pygame
from enums.phases import Phase
from manager.asset_manager import AssetManager
from manager.audio_manager import VOLUME_CHANNELS
from UI import Button, COLORS, Slider

CHANNEL_LABELS = {
    "music": "Music",
    "sfx": "SFX",
    "engine": "Engine",
    "wind": "Wind",
}


class OptionsScene:
    def __init__(self, screen, audio, on_phase_change=None):
        self.audio = audio
        self.on_phase_change = on_phase_change
        self.screen_width, self.screen_height = screen.get_size()
        self.center_x = self.screen_width / 2

        background_file = "Background_Slice_6.png"
        manager = AssetManager()
        self.background = manager.get_background(background_file)

        self._title_font = pygame.font.Font("fonts/Starjedi.ttf", 48)
        self._label_font = pygame.font.SysFont(None, 32)
        self._value_font = pygame.font.SysFont(None, 28)

        self.sliders = {}
        slider_width = 360
        slider_height = 24
        start_y = 320
        spacing = 70
        for index, channel in enumerate(VOLUME_CHANNELS):
            rect = pygame.Rect(0, 0, slider_width, slider_height)
            rect.center = (self.center_x + 40, start_y + index * spacing)
            self.sliders[channel] = Slider(
                rect,
                value=self.audio.get_volume(channel),
                on_change=lambda value, name=channel: self.audio.set_volume(name, value),
                fill_color=COLORS["yellow"],
            )

        self.back_button = Button(
            center=(self.center_x, start_y + len(VOLUME_CHANNELS) * spacing + 40),
            label="Back",
            on_click=self.go_back,
            padding=(20, 10),
            bg_color=COLORS["black"],
            text_color=COLORS["white"],
        )
        self.back_button.active = True

    def handle_event(self, event) -> bool:
        for slider in self.sliders.values():
            if slider.handle_event(event):
                return True
        return False

    def update(self, dt):
        self.back_button.update()

    def draw(self, screen):
        image_width = self.background.get_width()
        image_height = self.background.get_height()
        for x in range(0, self.screen_width, image_width):
            for y in range(0, self.screen_height, image_height):
                screen.blit(self.background, (x, y))

        title = self._title_font.render("Options", True, COLORS["yellow"])
        title_rect = title.get_rect(center=(self.center_x, 200))
        screen.blit(title, title_rect)

        for channel, slider in self.sliders.items():
            label = self._label_font.render(CHANNEL_LABELS[channel], True, COLORS["white"])
            label_rect = label.get_rect()
            label_rect.midright = (slider.rect.left - 24, slider.rect.centery)
            screen.blit(label, label_rect)

            percent = self._value_font.render(
                f"{int(round(slider.value * 100))}%", True, COLORS["white"]
            )
            percent_rect = percent.get_rect()
            percent_rect.midleft = (slider.rect.right + 16, slider.rect.centery)
            screen.blit(percent, percent_rect)

            slider.draw(screen)

        self.back_button.render(screen)

    def go_back(self):
        if self.on_phase_change:
            self.on_phase_change(Phase.MENU)
