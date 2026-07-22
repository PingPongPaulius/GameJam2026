import pygame


class Label:
    def __init__(self, text: str):
        self.font = pygame.font.Font(None, 16)
        self.text = text

    def render(self, g, hitbox):
        text = self.font.render(self.text, True, (0,0,0))
        g.blit(text, (hitbox.x+hitbox.w/4, hitbox.y+hitbox.h/3))


class Button:
    def __init__(self, x: int, y: int, w: int, h: int, c_s: int = 5, label = None, sprites: list = None):
        """
        Sprites should take in animation.load_sprites() output
        """
        self.hitbox = pygame.Rect(x, y, w, h)
        self.active = False
        self.cursor_size = c_s
        self.text = label
        self.sprites = sprites
        self.sprite_idx = 0
        self.states = ['Inactive', 'Hovered', 'Pressed', 'Idle']
        # Handle Labels, lazy solution
        if self.text is None and self.sprites is None:
            self.text = Label('')
        elif isinstance(self.text, str):
            self.text = Label(self.text)

    def update(self) -> str:

        if not self.active:
            return self.states[0]

        mouse_pos = pygame.mouse.get_pos()
        is_pressed = pygame.mouse.get_pressed()[0]

        mouse_on_button = self.hitbox.colliderect(pygame.Rect(mouse_pos[0], mouse_pos[1], self.cursor_size, self.cursor_size))

        if mouse_on_button:
            if is_pressed:
                return self.pressed()
            else:
                return self.hovered()
        else:
            return self.idle()
    
    def hovered(self):
        self.sprite_idx = 1
        return self.states[1]

    def pressed(self):
        self.sprite_idx = 2
        return self.states[2]

    def idle(self):
        self.sprite_idx = 0
        return self.states[3]

    def render(self, g):
        if self.sprites:
            g.blit(self.sprites[self.sprite_idx], self.hitbox)
        else:
            pygame.draw.rect(g, (255, 0, 0), self.hitbox)
            self.text.render(g, self.hitbox)

