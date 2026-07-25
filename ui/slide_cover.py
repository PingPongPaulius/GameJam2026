import pygame


class SlideCover:
    def __init__(self, rect, direction="down", duration=500, frames=None):
        """
        rect: pygame.Rect - the final covered position/size (also used as draw mask)
        direction: "down" or "up" - which way it slides to cover (ignored when frames are set)
        duration: animation duration in ms
        frames: optional list of Surfaces sized to rect; when set, plays frames instead of sliding
        """
        self.rect = pygame.Rect(rect)
        self.direction = direction
        self.duration = duration
        self.frames = list(frames) if frames else None
        self.frame_index = 0

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
        """Start the slide-in / close animation."""
        if not self.covered:
            self.active = True
            self.start_time = pygame.time.get_ticks()
            self.frame_index = 0

    def reset(self):
        """Snap the cover back open (unlocked)."""
        self.active = False
        self.covered = False
        self.frame_index = 0
        self.current_rect = self.start_rect.copy()

    def update(self):
        if not self.active:
            return

        elapsed = pygame.time.get_ticks() - self.start_time
        t = min(elapsed / self.duration, 1.0)

        if self.frames:
            n = len(self.frames)
            self.frame_index = min(int(t * n), n - 1)
            if t >= 1.0:
                self.active = False
                self.covered = True
                self.frame_index = n - 1
            return

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

        if self.frames:
            surface.blit(self.frames[self.frame_index], self.rect)
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
        if not self.covered:
            return False
        if self.frames:
            return self.rect.collidepoint(point)
        return self.current_rect.collidepoint(point)
