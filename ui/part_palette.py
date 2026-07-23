from collections import defaultdict
from dataclasses import dataclass

import pygame

from rocket.part_data import PartDef
from rocket.part_types import PartType


TYPE_ORDER = [
    PartType.NOSE_CONE,
    PartType.FUEL_TANK,
    PartType.ENGINE,
    PartType.FIN,
    PartType.BOOSTER,
    PartType.PARACHUTE,
    PartType.PAYLOAD,
]


class PalettePartUI:
    def __init__(self, part_def, rect):
        self.part_def = part_def
        self.rect = rect


@dataclass
class PaletteSection:
    part_type: PartType
    title: str
    header_rect: pygame.Rect
    items: list[PalettePartUI]


class PartPalette:
    TOP_LEFT = (20, 60)
    ITEM_SIZE = (64, 64)
    PARTS_PER_ROW = 3
    PADDING = 10
    BACKGROUND_PADDING = 12
    SECTION_HEADER_HEIGHT = 24
    SECTION_GAP = 10

    def __init__(
        self,
        part_defs,
        assets,
        top_left=TOP_LEFT,
        item_size=ITEM_SIZE,
        padding=PADDING,
        parts_per_row=PARTS_PER_ROW,
        background_padding=BACKGROUND_PADDING,
    ):
        self.assets = assets
        self.items = []
        self.sections: list[PaletteSection] = []
        self.hovered_item = None
        self.parts_per_row = max(1, parts_per_row)
        self.background_padding = background_padding
        self.background_rect = pygame.Rect(top_left, (0, 0))
        self._title_font = pygame.font.SysFont(None, 28)
        self._section_font = pygame.font.SysFont(None, 24)
        self._label_font = pygame.font.SysFont(None, 22)
        self._value_font = pygame.font.SysFont(None, 22)

        self._build_sections(part_defs, top_left, item_size, padding)

        if self.items:
            self.background_rect = self._compute_background_rect()

    def _group_part_defs(self, part_defs) -> list[tuple[PartType, list[PartDef]]]:
        grouped = defaultdict(list)
        for part_def in part_defs:
            grouped[part_def.part_type].append(part_def)

        ordered = [(part_type, grouped[part_type]) for part_type in TYPE_ORDER if grouped[part_type]]
        for part_type, defs in grouped.items():
            if part_type not in TYPE_ORDER:
                ordered.append((part_type, defs))
        return ordered

    def _format_part_type(self, part_type: PartType) -> str:
        return part_type.name.replace("_", " ").title()

    def _build_sections(self, part_defs, top_left, item_size, padding):
        origin_x, origin_y = top_left
        w, h = item_size
        y = origin_y
        grid_width = self.parts_per_row * w + (self.parts_per_row - 1) * padding

        for part_type, defs in self._group_part_defs(part_defs):
            title = self._format_part_type(part_type)
            header_rect = pygame.Rect(origin_x, y, grid_width, self.SECTION_HEADER_HEIGHT)
            y += self.SECTION_HEADER_HEIGHT + padding // 2

            section_items = []
            for index, part_def in enumerate(defs):
                col = index % self.parts_per_row
                row = index // self.parts_per_row
                x = origin_x + col * (w + padding)
                item_y = y + row * (h + padding)
                item = PalettePartUI(part_def, pygame.Rect(x, item_y, w, h))
                section_items.append(item)
                self.items.append(item)

            row_count = (len(defs) + self.parts_per_row - 1) // self.parts_per_row
            y += row_count * h + max(0, row_count - 1) * padding + self.SECTION_GAP

            self.sections.append(PaletteSection(part_type, title, header_rect, section_items))

    def _compute_background_rect(self) -> pygame.Rect:
        rects = [item.rect for item in self.items]
        rects.extend(section.header_rect for section in self.sections)
        left = min(rect.left for rect in rects)
        top = min(rect.top for rect in rects)
        right = max(rect.right for rect in rects)
        bottom = max(rect.bottom for rect in rects)
        rect = pygame.Rect(left, top, right - left, bottom - top)
        return rect.inflate(self.background_padding * 2, self.background_padding * 2)

    def update_hover(self, mouse_pos):
        self.hovered_item = self.item_at(mouse_pos)

    def _draw_background(self, surface):
        if not self.items:
            return

        rect = self.background_rect
        shadow = rect.move(3, 3)
        pygame.draw.rect(surface, (10, 12, 18), shadow, border_radius=8)

        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((35, 40, 52, 220))
        surface.blit(panel, rect.topleft)
        pygame.draw.rect(surface, (90, 100, 120), rect, 2, border_radius=8)

    def _draw_sections(self, surface):
        for index, section in enumerate(self.sections):
            header = section.header_rect
            title = self._section_font.render(section.title, True, (190, 200, 220))
            surface.blit(title, (header.x, header.y + 4))

            line_y = header.bottom - 2
            pygame.draw.line(
                surface,
                (70, 80, 100),
                (header.x, line_y),
                (header.right, line_y),
                1,
            )

    def draw(self, surface):
        self._draw_background(surface)
        self._draw_sections(surface)
        for item in self.items:
            image = self.assets.get_image(item.part_def.sprite)
            surface.blit(pygame.transform.smoothscale(image, item.rect.size), item.rect)
            border_color = (180, 210, 255) if item is self.hovered_item else (255, 255, 255)
            pygame.draw.rect(surface, border_color, item.rect, 0 if item is self.hovered_item else 1)

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

        subtitle = self._label_font.render(self._format_part_type(part.part_type), True, (150, 165, 190))
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
