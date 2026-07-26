import pygame
import sys
from enums.phases import Phase
from manager.asset_manager import AssetManager
from UI import Button, COLORS

class MainMenuScene:
    def __init__(self, screen, on_phase_change=None, can_start=None):
        self.on_phase_change = on_phase_change
        self.can_start = can_start
        self.status_text = "Loading parts & pilots..."
        self.game_title = "60 seconds to launch"
        self.game_title_font= "Starjedi"
        self.game_title_font_size = 60
        background_file = "Background_Slice_6.png"
        manager = AssetManager()
        self.background = manager.get_background(background_file)
        self.buttons = {}
        self.screen_width, self.screen_height = screen.get_size()
        self.center_x = self.screen_width / 2
        self._status_font = pygame.font.SysFont(None, 24)

        self.title_y = 160
        self.button_y_start = 300
        button_spacing = 10
        button_padding = (20, 10)

        self.buttons = self._create_menu_buttons(
            [
                ("Start game", self.start_game),
                ("Story", self.open_story),
                ("Options", self.open_options),
                ("Credits", self.show_credits),
                ("Missions", self.show_pilots),
                ("Quit", self.quit_game),
            ],
            self.center_x, self.button_y_start, button_spacing, padding=button_padding,
            bg_color=COLORS["black"], text_color=COLORS["white"]
        )
        self._start_button = self.buttons[0]

    def update(self, dt):
        ready = True if self.can_start is None else bool(self.can_start())
        self._start_button.active = ready
        for button in self.buttons:
            button.update()

    def _sync_layout(self, screen):
        width, height = screen.get_size()
        if (width, height) == (self.screen_width, self.screen_height):
            return
        self.screen_width, self.screen_height = width, height
        self.center_x = width / 2
        for button in self.buttons:
            button.hitbox.centerx = int(self.center_x)

    def draw(self, screen):
        self._sync_layout(screen)

        image_width = self.background.get_width()
        image_height = self.background.get_height()

        for x in range(0, self.screen_width, image_width):
            for y in range(0, self.screen_height, image_height):
                screen.blit(self.background, (x, y))

        font = pygame.font.Font("fonts/" + self.game_title_font + ".ttf", self.game_title_font_size)
        game_title = font.render(self.game_title.title(), True, COLORS["yellow"])
        title_rect = game_title.get_rect(center=(self.center_x, self.title_y))
        screen.blit(game_title, title_rect)

        for button in self.buttons:
            button.render(screen)

        if self.status_text:
            status_surf = self._status_font.render(self.status_text, True, COLORS["white"])
            status_rect = status_surf.get_rect(center=(self.center_x, self.screen_height - 40))
            screen.blit(status_surf, status_rect)

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
        if self.can_start is not None and not self.can_start():
            return
        print("Starting game!")
        if self.on_phase_change:
            self.on_phase_change(Phase.BUILD)

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
