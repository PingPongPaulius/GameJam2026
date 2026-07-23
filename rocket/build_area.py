import math

import pygame

class BuildArea:
    """Defines the vertical stack slots the rocket is assembled into."""
    def __init__(
        self,
        anchor_pos,
        slot_height=64,
        slot_count=6,
        padding=16,
        horizontal_snap_points=3,
        horizontal_snap_span=None,
        horizontal_snap_step_size=None,
        side_attach_offset=None,
        enable_snap_draws=False,
    ):
        self.anchor_x, self.anchor_y = anchor_pos
        self.slot_height = slot_height
        self.slot_count = slot_count
        self.padding = padding
        self.horizontal_snap_points = max(1, horizontal_snap_points)
        step_size = horizontal_snap_step_size or slot_height / 4
        self.horizontal_snap_span = (
            horizontal_snap_span
            if horizontal_snap_span is not None
            else step_size * (self.horizontal_snap_points - 1)
        )
        self.side_attach_offset = side_attach_offset or slot_height * 0.6
        self.enable_snap_draws = enable_snap_draws

    def horizontal_snap_step(self) -> float:
        if self.horizontal_snap_points <= 1:
            return 0.0
        return self.horizontal_snap_span / (self.horizontal_snap_points - 1)

    def _center_offset_values(self):
        if self.horizontal_snap_points <= 1:
            return [0.0]
        step = self.horizontal_snap_step()
        half = (self.horizontal_snap_points - 1) / 2
        values = [(i - half) * step for i in range(self.horizontal_snap_points)]
        if not any(abs(v) < 0.01 for v in values):
            closest = min(range(len(values)), key=lambda i: abs(values[i]))
            values[closest] = 0.0
        return values

    def max_center_offset(self) -> float:
        values = self._center_offset_values()
        return max(abs(v) for v in values)

    def slot_screen_pos(self, slot_index, offset_x=0.0):
        x = self.anchor_x + offset_x
        y = self.anchor_y - slot_index * self.slot_height
        return x, y

    def bounds_rect(self) -> pygame.Rect:
        half_w = max(
            int(self.max_center_offset() + self.slot_height // 2),
            int(self.side_attach_offset + self.slot_height // 2),
        )
        top = (
            self.anchor_y
            - (self.slot_count - 1) * self.slot_height
            - self.slot_height // 2
            - self.padding
        )
        bottom = self.anchor_y + self.slot_height // 2 + self.padding
        left = self.anchor_x - half_w - self.padding
        width = (half_w + self.padding) * 2
        return pygame.Rect(left, top, width, bottom - top)

    def draw(self, surface):
        rect = self.bounds_rect()
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((35, 40, 52, 220))
        surface.blit(panel, rect.topleft)
        pygame.draw.rect(surface, (90, 100, 120), rect, 2, border_radius=8)

        for slot in range(self.slot_count):
            _, y = self.slot_screen_pos(slot)
            line_rect = pygame.Rect(
                rect.left + 12,
                int(y) - 1,
                rect.width - 24,
                2,
            )
            pygame.draw.rect(surface, (60, 68, 82), line_rect)

            for offset_x in self._center_offset_values():
                x, sub_y = self.slot_screen_pos(slot, offset_x)
                color = (120, 130, 150) if offset_x == 0.0 else (75, 82, 96)
                if self.enable_snap_draws:
                    pygame.draw.circle(surface, color, (int(x), int(sub_y)), 3)

            for side in (-1, 1):
                x, side_y = self.slot_screen_pos(slot, side * self.side_attach_offset)
                if self.enable_snap_draws:
                    pygame.draw.rect(
                        surface,
                        (100, 160, 100),
                        pygame.Rect(int(x) - 4, int(side_y) - 4, 8, 8),
                        1,
                    )

    def snap_offsets_adjacent(self, offset_a, offset_b) -> bool:
        if abs(offset_a - offset_b) < 0.01:
            return True
        values = self._center_offset_values()
        idx_a = min(range(len(values)), key=lambda i: abs(values[i] - offset_a))
        idx_b = min(range(len(values)), key=lambda i: abs(values[i] - offset_b))
        return abs(idx_a - idx_b) <= 1

    def is_side_offset(self, offset_x) -> bool:
        return abs(abs(offset_x) - self.side_attach_offset) < 0.01

    def slot_at(self, mouse_pos, side_mount=False):
        """Returns (slot_index, offset_x) for a mouse position, or (None, 0)."""
        mx, my = mouse_pos
        rel_y = self.anchor_y - my
        slot = round(rel_y / self.slot_height)
        if not (0 <= slot < self.slot_count):
            return None, 0.0

        dx = mx - self.anchor_x

        if side_mount:
            if abs(dx) <= self.max_center_offset() + self.slot_height // 4:
                return None, 0.0
            return slot, math.copysign(self.side_attach_offset, dx)

        offset_x = min(self._center_offset_values(), key=lambda o: abs(dx - o))
        return slot, offset_x
