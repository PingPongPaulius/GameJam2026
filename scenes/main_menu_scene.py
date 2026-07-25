import pygame
import sys
from enums.phases import Phase
from manager.asset_manager import AssetManager
from UI import Button, COLORS

class MainMenuScene:
    def __init__(self, screen, on_phase_change=None):
        self.on_phase_change = on_phase_change
        self.game_title = "60 seconds to launch"
        self.game_title_font= "Starjedi"
        self.game_title_font_size = 60
        background_file = "Background_Slice_6.png"
        manager = AssetManager()
        self.background = manager.get_background(background_file)
        self.buttons = {}
        self.screen_width, self.screen_height = screen.get_size()
        self.center_x = self.screen_width / 2

        button_y_start = 300
        button_spacing = 10
        button_padding = (20, 10)
        
        self.buttons = self._create_menu_buttons(
            [
                ("Start game", self.start_game),
                ("Options", self.open_options),
                ("Quit", self.quit_game),
            ],
            self.center_x, button_y_start, button_spacing, padding=button_padding,
            bg_color=COLORS["black"], text_color=COLORS["white"]
        )

    def update(self, dt):
        for button in self.buttons:
            button.update()

    def draw(self, screen):
        image_width = self.background.get_width()
        image_height = self.background.get_height()

        for x in range(0, self.screen_width, image_width):
            for y in range(0, self.screen_height, image_height):
                screen.blit(self.background, (x, y))
        
        font = pygame.font.Font("fonts/" + self.game_title_font + ".ttf", self.game_title_font_size)
        game_title = font.render(self.game_title.title(), True, COLORS["yellow"])
        title_rect = game_title.get_rect(center=(self.center_x, y + 200))
        screen.blit(game_title, title_rect)

        for button in self.buttons:
            button.render(screen)

    def _create_menu_buttons(self, items, center_x, start_y, spacing=20, padding=(20, 10),
                    bg_color=(200, 200, 200), text_color=(255, 255, 255)):
        buttons = []
        y = start_y
        for label, callback in items:
            button = Button(center=(center_x, y), label=label, on_click=callback,
                            padding=padding, bg_color=bg_color, text_color=text_color)
            button.active = True
            buttons.append(button)
            y += button.hitbox.height + spacing
        return buttons

    def start_game(self):
        print("Starting game!")  # swap for scene transition
        if self.on_phase_change:
            self.on_phase_change(Phase.BUILD)

    def open_options(self):
        print("Opening options!")

    def quit_game(self):
        pygame.quit()
        sys.exit()