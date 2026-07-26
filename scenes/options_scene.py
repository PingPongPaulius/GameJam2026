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
        self.back_button = None
        self._build_layout()

    def _build_layout(self):
        """(Re)build every rect that depends on self.center_x. Called on init
        and whenever the window is resized, so subclasses should override
        this (calling super()._build_layout() first) rather than draw()."""
        slider_width = 360
        slider_height = 24
        start_y = 320
        spacing = 70
        self.sliders = {}
        for index, channel in enumerate(VOLUME_CHANNELS):
            rect = pygame.Rect(0, 0, slider_width, slider_height)
            rect.center = (self.center_x + 40, start_y + index * spacing)
            self.sliders[channel] = Slider(
                rect,
                value=self.audio.get_volume(channel),
                on_change=lambda value, name=channel: self.audio.set_volume(name, value),
                fill_color=COLORS["yellow"],
            )

        back_center = (self.center_x, start_y + len(VOLUME_CHANNELS) * spacing + 40)
        if self.back_button is None:
            self.back_button = Button(
                center=back_center,
                label="Back",
                on_click=self.go_back,
                padding=(20, 10),
                bg_color=COLORS["black"],
                text_color=COLORS["white"],
            )
            self.back_button.active = True
        else:
            self.back_button.hitbox.center = back_center

    def _sync_layout(self, screen):
        width, height = screen.get_size()
        if (width, height) == (self.screen_width, self.screen_height):
            return
        self.screen_width, self.screen_height = width, height
        self.center_x = width / 2
        self._build_layout()

    def handle_event(self, event) -> bool:
        for slider in self.sliders.values():
            if slider.handle_event(event):
                return True
        return False

    def update(self, dt):
        self.back_button.update()

    def draw(self, screen):
        self._sync_layout(screen)

        image_width = self.background.get_width()
        image_height = self.background.get_height()
        for x in range(0, self.screen_width, image_width):
            for y in range(0, self.screen_height, image_height):
                screen.blit(self.background, (x, y))

        title = self._title_font.render("options", True, COLORS["yellow"])
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


class CreditsScene(OptionsScene):
    SECTIONS = [
        ("programmers", ["p1ngp0ng", "mrt", "dopiepanda"]),
        ("graphics", ["garcherblu"]),
        ("production manager", ["kot"]),
        ("music", ["grand_project (pixabay)"]),
        ("sound effects", [
            "freesound_community (pixabay)",
            "soundreality (pixabay)",
            "dragon-studio (pixabay)",
        ]),
    ]
    SCROLL_SPEED = 55

    def __init__(self, screen, audio, on_phase_change=None):
        super().__init__(screen, audio, on_phase_change)
        self._header_font = pygame.font.Font("fonts/Starjedi.ttf", 80)
        self._name_font = pygame.font.Font("fonts/Starjedi.ttf", 44)
        self.credits_surface = self._build_credits_surface()
        self._overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 120))
        self.scroll = 0.0
        self.back_button.hitbox.center = (self.center_x, self.screen_height - 40)
        self.reset()

    def reset(self):
        # Start slightly before the first line so credits rise from the bottom.
        self.scroll = -40.0

    def _build_credits_surface(self):
        lines = []
        for section, names in self.SECTIONS:
            lines.append(("header", section))
            lines.append(("spacer", None))
            for name in names:
                lines.append(("name", name))
            lines.append(("spacer", None))
            lines.append(("spacer", None))

        # Size the surface to the widest line so long headers aren't clipped.
        max_width = 0
        for kind, text in lines:
            if kind == "spacer":
                continue
            font = self._header_font if kind == "header" else self._name_font
            max_width = max(max_width, font.size(text)[0])
        crawl_width = min(self.screen_width - 40, max_width + 48)

        line_height = 88
        height = max(line_height, len(lines) * line_height + 80)
        surface = pygame.Surface((crawl_width, height), pygame.SRCALPHA)

        y = 20
        for kind, text in lines:
            if kind == "spacer":
                y += line_height // 2
                continue
            if kind == "header":
                rendered = self._header_font.render(text, True, COLORS["yellow"])
            else:
                rendered = self._name_font.render(text, True, COLORS["white"])
            rect = rendered.get_rect(midtop=(crawl_width // 2, y))
            surface.blit(rendered, rect)
            y += line_height

        return surface

    def update(self, dt):
        super().update(dt)
        self.scroll += self.SCROLL_SPEED * dt
        # Loop after the crawl has fully receded into the distance.
        if self.scroll > self.credits_surface.get_height() + 80:
            self.reset()

    def _draw_crawl(self, screen):
        w = self.screen_width
        h = self.screen_height
        # Crawl from the bottom up toward the title, with mild perspective.
        vanish_y = int(h * 0.20)
        surf = self.credits_surface
        sw, sh = surf.get_size()
        floor_y = h - 70  # enter from above the back button

        for screen_y in range(floor_y, vanish_y, -1):
            depth = (screen_y - vanish_y) / (floor_y - vanish_y)
            depth = max(0.001, depth)
            # Mild foreshortening so the plane is less tilted.
            scale = depth ** 0.85

            dist_from_floor = floor_y - screen_y
            # Subtract so lines travel from the near plane up into the distance.
            src_y = int(self.scroll - dist_from_floor / (scale ** 0.75))
            if src_y < 0 or src_y >= sh:
                continue

            scaled_w = max(2, int(sw * (0.45 + 0.55 * scale)))
            row = surf.subsurface(pygame.Rect(0, src_y, sw, 1)).copy()
            scaled = pygame.transform.smoothscale(row, (scaled_w, 1))

            # Fade out as lines approach the horizon.
            alpha = min(255, int(260 * scale))
            if alpha < 255:
                scaled.set_alpha(alpha)

            screen.blit(scaled, ((w - scaled_w) // 2, screen_y))

    def draw(self, screen):
        self._sync_layout(screen)

        image_width = self.background.get_width()
        image_height = self.background.get_height()
        for x in range(0, self.screen_width, image_width):
            for y in range(0, self.screen_height, image_height):
                screen.blit(self.background, (x, y))

        # Soft vignette so the crawl reads more clearly over the background.
        screen.blit(self._overlay, (0, 0))

        title = self._title_font.render("credits", True, COLORS["yellow"])
        title_rect = title.get_rect(center=(self.center_x, 100))
        screen.blit(title, title_rect)

        self._draw_crawl(screen)
        self.back_button.render(screen)


class PilotsScene(OptionsScene):
    SUBTITLE = "Pilot Bonus Objectives"
    MISSIONS = [
        ("Pilot_Human.png", "Human Master Builder: Assemble a starship using at least 5 unique components."),
        ("Pilot_Alien.png", "Alien Hyperspace Assembly: Complete your ship build in under 10 seconds."),
        ("Pilot_Robot.png", "Robot Juiced Up: Equip your ship build with a functional battery."),
    ]

    def __init__(self, screen, audio, on_phase_change=None):
        super().__init__(screen, audio, on_phase_change)
        self._subtitle_font = pygame.font.SysFont(None, 32)
        self._mission_font = pygame.font.SysFont(None, 30)
        assets = AssetManager()

        box_width = min(780, self.screen_width - 120)
        box_height = 88
        box_gap = 18
        portrait_size = 64
        start_y = 320
        left = int(self.center_x - box_width / 2)

        self.mission_boxes = []
        for index, (avatar, text) in enumerate(self.MISSIONS):
            rect = pygame.Rect(left, start_y + index * (box_height + box_gap), box_width, box_height)
            portrait = assets.get_pilot_image(avatar)
            scale = min(portrait_size / portrait.get_width(), portrait_size / portrait.get_height())
            size = (max(1, int(portrait.get_width() * scale)), max(1, int(portrait.get_height() * scale)))
            portrait = pygame.transform.smoothscale(portrait, size)
            self.mission_boxes.append((rect, portrait, text))

        last_bottom = self.mission_boxes[-1][0].bottom if self.mission_boxes else start_y
        self.back_button.hitbox.center = (self.center_x, last_bottom + 50)

    def draw(self, screen):
        self._sync_layout(screen)

        image_width = self.background.get_width()
        image_height = self.background.get_height()
        for x in range(0, self.screen_width, image_width):
            for y in range(0, self.screen_height, image_height):
                screen.blit(self.background, (x, y))

        title = self._title_font.render("secret missions", True, COLORS["yellow"])
        title_rect = title.get_rect(center=(self.center_x, 200))
        screen.blit(title, title_rect)

        subtitle = self._subtitle_font.render(self.SUBTITLE, True, COLORS["white"])
        subtitle_rect = subtitle.get_rect(center=(self.center_x, 270))
        screen.blit(subtitle, subtitle_rect)

        for rect, portrait, text in self.mission_boxes:
            shadow = rect.move(3, 3)
            pygame.draw.rect(screen, (10, 12, 18), shadow, border_radius=10)
            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            panel.fill((28, 32, 42, 230))
            screen.blit(panel, rect.topleft)
            pygame.draw.rect(screen, (100, 120, 160), rect, 2, border_radius=10)

            portrait_rect = portrait.get_rect()
            portrait_rect.midleft = (rect.left + 16, rect.centery)
            screen.blit(portrait, portrait_rect)

            label = self._mission_font.render(text, True, COLORS["white"])
            label_rect = label.get_rect()
            label_rect.midleft = (portrait_rect.right + 18, rect.centery)
            screen.blit(label, label_rect)

        self.back_button.render(screen)

class StoryScene(OptionsScene):

    def __init__(self, screen, audio, on_phase_change=None):
        super().__init__(screen, audio, on_phase_change)
        manager = AssetManager()
        comic = manager.get_background("Story_Comic.png")

        # Leave room below the comic for the back button.
        max_width = self.screen_width - 40
        max_height = self.screen_height - 100
        scale = min(max_width / comic.get_width(), max_height / comic.get_height(), 1.0)
        size = (int(comic.get_width() * scale), int(comic.get_height() * scale))
        self.story_image = pygame.transform.smoothscale(comic, size)
        self.story_rect = self.story_image.get_rect(
            center=(self.center_x, (self.screen_height - 60) / 2)
        )
        self.back_button.hitbox.center = (self.center_x, self.story_rect.bottom + 30)

    def draw(self, screen):
        image_width = self.background.get_width()
        image_height = self.background.get_height()
        for x in range(0, self.screen_width, image_width):
            for y in range(0, self.screen_height, image_height):
                screen.blit(self.background, (x, y))

        screen.blit(self.story_image, self.story_rect)
        self.back_button.render(screen)