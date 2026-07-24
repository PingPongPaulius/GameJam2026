import pygame

class SlideCover:
    def __init__(self, rect, direction="down", duration=500):
        """
        rect: pygame.Rect - the final covered position/size (also used as draw mask)
        direction: "down" or "up" - which way it slides to cover
        duration: animation duration in ms
        """
        self.rect = pygame.Rect(rect)
        self.direction = direction
        self.duration = duration

        # Start position is off-screen (above or below the target)
        self.start_rect = self.rect.copy()
        if direction == "down":
            self.start_rect.y = self.rect.y - self.rect.height  # starts above
        else:
            self.start_rect.y = self.rect.y + self.rect.height  # starts below

        self.current_rect = self.start_rect.copy()

        self.active = False
        self.start_time = 0
        self.covered = False  # True once animation finishes and it's blocking input

    def trigger(self):
        """Start the slide-in animation."""
        if not self.covered:
            self.active = True
            self.start_time = pygame.time.get_ticks()

    def update(self):
        if not self.active:
            return

        elapsed = pygame.time.get_ticks() - self.start_time
        t = min(elapsed / self.duration, 1.0)

        # Ease-out cubic for a nice deceleration feel
        eased_t = 1 - (1 - t) ** 3

        # Lerp y position
        start_y = self.start_rect.y
        end_y = self.rect.y
        self.current_rect.y = int(start_y + (end_y - start_y) * eased_t)
        self.current_rect.x = self.rect.x
        self.current_rect.width = self.rect.width
        self.current_rect.height = self.rect.height

        if t >= 1.0:
            self.active = False
            self.covered = True  # now it's fully blocking

    def draw(self, surface, image=None, color=(40, 40, 40)):
        if not (self.active or self.covered):
            return

        # Clip to the panel so the cover appears to emerge from the top edge
        # instead of being visible above the palette while sliding in.
        prev_clip = surface.get_clip()
        surface.set_clip(self.rect.clip(prev_clip))
        try:
            if image:
                surface.blit(image, self.current_rect)
            else:
                pygame.draw.rect(surface, color, self.current_rect)
        finally:
            surface.set_clip(prev_clip)

    def is_blocking(self, point):
        """Check if a point (e.g. mouse click) is blocked by the cover."""
        return self.covered and self.current_rect.collidepoint(point)
