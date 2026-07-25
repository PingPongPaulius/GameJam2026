import pygame


COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0)
}

class Label:
    def __init__(self, text: str, font: pygame.font.Font = None, color: tuple = (255, 255, 255)):
        self.text = text
        self.font = font if font is not None else pygame.font.Font(pygame.font.get_default_font(), 24)
        self.color = color

    def get_size(self):
        return self.font.size(self.text)

    def render(self, g, hitbox, color: tuple = None):
        color = color if color is not None else self.color
        text = self.font.render(self.text, True, color)
        text_rect = text.get_rect(center=hitbox.center)
        g.blit(text, text_rect)


class Button:
    def __init__(self, x: int = None, y: int = None, w: int = None, h: int = None, c_s: int = 5, 
                 label = None, sprites: list = None, padding: tuple = (20, 10), center: tuple = None, 
                 on_click=None, bg_color=(200, 200, 200), text_color=(255, 255, 255)):
        """
        Sprites should take in animation.load_sprites() output
        """
        self.active = False
        self.cursor_size = c_s
        self.text = label
        self.sprites = sprites
        self.sprite_idx = 0
        self.states = ['Inactive', 'Hovered', 'Pressed', 'Idle']
        self.on_click = on_click
        self._was_pressed = False

        self.bg_color = bg_color
        self.text_color = text_color
        self.current_bg_color = bg_color

        # Handle Labels, lazy solution
        if self.text is None and self.sprites is None:
            self.text = Label('')
        elif isinstance(self.text, str):
            self.text = Label(self.text)

        if w is None or h is None:
            text_w, text_h = self.text.get_size()
            w = w if w is not None else int(text_w + padding[0] * 2)
            h = h if h is not None else int(text_h + padding[1] * 2)

        if center is not None:
            self.hitbox = pygame.Rect(0, 0, w, h)
            self.hitbox.center = center
        else:
            self.hitbox = pygame.Rect(x, y, w, h)

    def update(self) -> str:
        if not self.active:
            self._was_pressed = False
            return self.states[0]

        mouse_pos = pygame.mouse.get_pos()
        is_pressed = pygame.mouse.get_pressed()[0]
        mouse_on_button = self.hitbox.collidepoint(mouse_pos)

        if mouse_on_button:
            if is_pressed:
                state = self.pressed()
            else:
                if self._was_pressed and self.on_click:
                    self.on_click()  # fires on release, i.e. an actual "click"
                state = self.hovered()
        else:
            state = self.idle()

        self._was_pressed = is_pressed and mouse_on_button
        return state
    
    def hovered(self):
        self.sprite_idx = 1
        self.current_bg_color = self.shade_color(self.bg_color, 30)
        return self.states[1]

    def pressed(self):
        self.sprite_idx = 2
        self.current_bg_color = self.shade_color(self.bg_color, -30)
        return self.states[2]

    def idle(self):
        self.sprite_idx = 0
        self.current_bg_color = self.bg_color
        return self.states[3]

    def render(self, g, bg_color: tuple = None, text_color: tuple = None):
        bg_color = bg_color if bg_color is not None else self.current_bg_color
        text_color = text_color if text_color is not None else self.text_color
        if self.sprites:
            g.blit(self.sprites[self.sprite_idx], self.hitbox)
        else:
            pygame.draw.rect(g, bg_color, self.hitbox)
            self.text.render(g, self.hitbox, text_color)

    def shade_color(self, color: tuple, amount: int) -> tuple:
        """Positive amount lightens, negative darkens."""
        return tuple(max(0, min(255, c + amount)) for c in color)


class Slider:
    """Horizontal volume-style slider. Value is 0.0–1.0."""

    TRACK_HEIGHT = 8
    HANDLE_RADIUS = 10

    def __init__(
        self,
        rect: pygame.Rect,
        value: float = 1.0,
        on_change=None,
        track_color=(80, 80, 80),
        fill_color=(220, 200, 40),
        handle_color=(255, 255, 255),
    ):
        self.rect = pygame.Rect(rect)
        self.value = max(0.0, min(1.0, value))
        self.on_change = on_change
        self.track_color = track_color
        self.fill_color = fill_color
        self.handle_color = handle_color
        self._dragging = False

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._hit_area().collidepoint(event.pos):
                self._dragging = True
                self._set_from_mouse(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging:
                self._dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self._set_from_mouse(event.pos[0])
            return True
        return False

    def draw(self, surface):
        track = pygame.Rect(
            self.rect.x,
            self.rect.centery - self.TRACK_HEIGHT // 2,
            self.rect.width,
            self.TRACK_HEIGHT,
        )
        pygame.draw.rect(surface, self.track_color, track, border_radius=4)
        fill_w = int(self.rect.width * self.value)
        if fill_w > 0:
            fill = pygame.Rect(track.x, track.y, fill_w, track.height)
            pygame.draw.rect(surface, self.fill_color, fill, border_radius=4)
        handle_x = self.rect.x + int(self.rect.width * self.value)
        pygame.draw.circle(
            surface, self.handle_color, (handle_x, self.rect.centery), self.HANDLE_RADIUS
        )

    def _hit_area(self) -> pygame.Rect:
        pad = self.HANDLE_RADIUS + 4
        return self.rect.inflate(pad * 2, pad * 2)

    def _set_from_mouse(self, mouse_x: int):
        if self.rect.width <= 0:
            return
        t = (mouse_x - self.rect.x) / self.rect.width
        value = max(0.0, min(1.0, t))
        if abs(value - self.value) < 1e-6:
            return
        self.value = value
        if self.on_change:
            self.on_change(self.value)
