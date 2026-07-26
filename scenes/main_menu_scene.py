import random
import sys

import pygame

from enums.phases import Phase
from manager.asset_manager import AssetManager
from rendering.flight_visuals import FlightVisuals
from UI import Button, COLORS

class MainMenuScene:
    def __init__(self, screen, on_phase_change=None, can_start=None):
        self.on_phase_change = on_phase_change
        self.can_start = can_start
        self.status_text = "Loading parts & pilots..."
        background_file = "Background_Slice_6.png"
        manager = AssetManager()
        self.background = manager.get_background(background_file)
        self._title_source = manager.get_background("game-title.png")
        self.title_image = self._title_source
        self.buttons = {}
        self.screen_width, self.screen_height = screen.get_size()
        self.center_x = self.screen_width / 2
        self._status_font = pygame.font.SysFont(None, 24)

        self.title_y = 160
        self.button_y_start = 300
        self.button_width = 220  # shared width for all menu buttons
        self.button_spacing = 10
        self._scale_title()
        self._button_sprite_sources = [
            pygame.image.load("Sprites/Button/Button_Neutral3.png").convert_alpha(),
            pygame.image.load("Sprites/Button/Button_Hover3.png").convert_alpha(),
            pygame.image.load("Sprites/Button/Button_Down3.png").convert_alpha(),
        ]
        self._button_sprites = self._scaled_button_sprites()

        self.buttons = self._create_menu_buttons(
            [
                ("Start game", self.start_game),
                ("Story", self.open_story),
                ("Options", self.open_options),
                ("Credits", self.show_credits),
                ("Missions", self.show_pilots),
                ("Quit", self.quit_game),
            ],
            self.center_x,
            self.button_y_start,
            self.button_spacing,
            sprites=self._button_sprites,
            text_color=COLORS["white"],
        )
        self._start_button = self.buttons[0]

        self.visuals = FlightVisuals(100_000, self.screen_width, self.screen_height)
        self.visuals.HEIGHT_BAND_SPRITES[5] = ["planet_1", "planet_2", "planet_3", "ufo"]
        self.visuals.sprite_images = {
            "ufo": pygame.image.load("Sprites/Background Clutter/Clutter_UFO.png").convert_alpha(),
            "planet_1": pygame.image.load("Sprites/Background Clutter/Clutter_Planet1.png").convert_alpha(),
            "planet_2": pygame.image.load("Sprites/Background Clutter/Clutter_Planet2.png").convert_alpha(),
            "planet_3": pygame.image.load("Sprites/Background Clutter/Clutter_Planet3.png").convert_alpha(),
        }
        self._spawn_timer = 0.0
        self._spawn_interval = random.uniform(8, 30)
        self.visuals._instantiate_new_visual()

    def update(self, dt):
        ready = True if self.can_start is None else bool(self.can_start())
        self._start_button.active = ready
        for button in self.buttons:
            button.update()

        self.visuals.update(dt)
        self._spawn_timer += dt
        if self._spawn_timer >= self._spawn_interval:
            self._spawn_timer = 0.0
            self._spawn_interval = random.uniform(2.0, 5.0)
            self.visuals._instantiate_new_visual()

    def _scale_title(self):
        max_width = max(1, int(self.screen_width * 0.7))
        src_w, src_h = self._title_source.get_size()
        if src_w <= max_width:
            self.title_image = self._title_source
            return
        scale = max_width / src_w
        size = (max_width, max(1, int(src_h * scale)))
        self.title_image = pygame.transform.smoothscale(self._title_source, size)

    def _scaled_button_sprites(self):
        src_w, src_h = self._button_sprite_sources[0].get_size()
        width = max(1, int(self.button_width))
        height = max(1, int(src_h * (width / src_w)))
        size = (width, height)
        return [
            pygame.transform.smoothscale(sprite, size)
            for sprite in self._button_sprite_sources
        ]

    def _sync_layout(self, screen):
        width, height = screen.get_size()
        if (width, height) == (self.screen_width, self.screen_height):
            return
        self.screen_width, self.screen_height = width, height
        self.center_x = width / 2
        self.visuals.screen_width = width
        self.visuals.screen_height = height
        self._scale_title()
        for button in self.buttons:
            button.hitbox.centerx = int(self.center_x)

    def draw(self, screen):
        self._sync_layout(screen)

        image_width = self.background.get_width()
        image_height = self.background.get_height()

        for x in range(0, self.screen_width, image_width):
            for y in range(0, self.screen_height, image_height):
                screen.blit(self.background, (x, y))

        self.visuals.draw(screen)

        title_rect = self.title_image.get_rect(center=(self.center_x, self.title_y))
        screen.blit(self.title_image, title_rect)

        for button in self.buttons:
            button.render(screen)

        if self.status_text:
            status_surf = self._status_font.render(self.status_text, True, COLORS["white"])
            status_rect = status_surf.get_rect(center=(self.center_x, self.screen_height - 40))
            screen.blit(status_surf, status_rect)

    def _create_menu_buttons(self, items, center_x, start_y, spacing=20,
                    sprites=None, text_color=(255, 255, 255)):
        buttons = []
        y = start_y
        width = max(1, int(self.button_width))
        height = sprites[0].get_height() if sprites else None
        for label, callback in items:
            button = Button(
                center=(center_x, y),
                w=width,
                h=height,
                label=label,
                on_click=callback,
                sprites=sprites,
                text_color=text_color,
            )
            button.active = True
            buttons.append(button)
            y += button.hitbox.height + spacing
        return buttons

    def start_game(self):
        if self.can_start is not None and not self.can_start():
            return
        print("Starting game!")
        if self.on_phase_change:
            self.on_phase_change(Phase.INTRO)

    def open_story(self):
        if self.on_phase_change:
            self.on_phase_change(Phase.STORY)

    def open_options(self):
        if self.on_phase_change:
            self.on_phase_change(Phase.OPTIONS)

    def show_credits(self):
        if self.on_phase_change:
            self.on_phase_change(Phase.CREDITS)
    
    def show_pilots(self):
        if self.on_phase_change:
            self.on_phase_change(Phase.PILOTS)

    def quit_game(self):
        pygame.quit()
        sys.exit()
