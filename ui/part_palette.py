import pygame

from rocket.part_data import PartDef


class PalettePartUI:
    def __init__(self, part_def, rect):
        self.part_def = part_def
        self.rect = rect

class PartPalette:
    TOP_LEFT = (20, 60)
    ITEM_SIZE = (64, 64)
    PADDING = 10

    def __init__(self, part_defs, assets, top_left=TOP_LEFT, item_size=ITEM_SIZE, padding=PADDING):
        self.assets = assets
        self.items = []
        self.hovered_item = None
        self._title_font = pygame.font.SysFont(None, 28)
        self._label_font = pygame.font.SysFont(None, 22)
        self._value_font = pygame.font.SysFont(None, 22)
        x, y = top_left
        w, h = item_size
        for part_def in part_defs:
            self.items.append(PalettePartUI(part_def, pygame.Rect(x, y, w, h)))
            y += h + padding

    def update_hover(self, mouse_pos):
        self.hovered_item = self.item_at(mouse_pos)

    def draw(self, surface):
        for item in self.items:
            image = self.assets.get_image(item.part_def.sprite)
            surface.blit(pygame.transform.smoothscale(image, item.rect.size), item.rect)
            border_color = (180, 210, 255) if item is self.hovered_item else (255, 255, 255)
            pygame.draw.rect(surface, border_color, item.rect, 2 if item is self.hovered_item else 1)

    def draw_tooltip(self, surface):
        if self.hovered_item is None:
            return

        part = self.hovered_item.part_def
        lines = self._stat_lines(part)
        self._draw_tooltip_panel(surface, self.hovered_item.rect, part, lines)

    def _stat_lines(self, part: PartDef) -> list[tuple[str, str]]:
        lines = [("Weight", f"{part.weight:.1f}")]
        if part.thrust > 0:
            lines.append(("Thrust", f"{part.thrust:.0f}"))
        if part.fuel_capacity > 0:
            lines.append(("Fuel", f"{part.fuel_capacity:.0f}"))
        if part.stability_contribution > 0:
            lines.append(("Stability", f"+{part.stability_contribution:.1f}"))
        if part.heat_dissipation > 0:
            lines.append(("Heat dissipation", f"{part.heat_dissipation:.1f}"))
        return lines

    def _format_part_type(self, part: PartDef) -> str:
        return part.part_type.name.replace("_", " ").title()

    def _draw_tooltip_panel(
        self,
        surface,
        anchor_rect: pygame.Rect,
        part: PartDef,
        lines: list[tuple[str, str]],
    ):
        padding = 12
        line_height = 24
        title_height = 30
        subtitle_height = 22
        stat_count = max(len(lines), 1)
        panel_w = 220
        panel_h = padding * 2 + title_height + subtitle_height + stat_count * line_height

        panel_x = anchor_rect.right + 14
        panel_y = anchor_rect.top
        if panel_x + panel_w > surface.get_width():
            panel_x = anchor_rect.left - panel_w - 14
        panel_y = max(8, min(panel_y, surface.get_height() - panel_h - 8))

        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        shadow = panel_rect.move(3, 3)
        pygame.draw.rect(surface, (10, 12, 18), shadow, border_radius=8)
        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel.fill((28, 32, 42, 245))
        surface.blit(panel, panel_rect.topleft)
        pygame.draw.rect(surface, (100, 120, 160), panel_rect, 2, border_radius=8)

        x = panel_rect.x + padding
        y = panel_rect.y + padding

        title = self._title_font.render(part.name, True, (240, 244, 252))
        surface.blit(title, (x, y))
        y += title_height

        subtitle = self._label_font.render(self._format_part_type(part), True, (150, 165, 190))
        surface.blit(subtitle, (x, y))
        y += subtitle_height

        pygame.draw.line(
            surface,
            (70, 80, 100),
            (panel_rect.x + padding, y - 4),
            (panel_rect.right - padding, y - 4),
            1,
        )

        for label, value in lines:
            label_surf = self._label_font.render(label, True, (170, 180, 200))
            value_surf = self._value_font.render(value, True, (230, 236, 248))
            surface.blit(label_surf, (x, y))
            surface.blit(value_surf, (panel_rect.right - padding - value_surf.get_width(), y))
            y += line_height

    def item_at(self, pos):
        for item in self.items:
            if item.rect.collidepoint(pos):
                return item
        return None
