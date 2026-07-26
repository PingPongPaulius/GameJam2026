import pygame

from rocket.pilot import Pilot
from ui.part_palette import PartPalette
from ui.slide_cover import SlideCover

SOURCE_SIZE = (420, 1080)
PILOT_REGION = pygame.Rect(32, 28, 356, 300)
ATTR_REGION = pygame.Rect(32, 340, 356, 88)
PARTS_REGION = pygame.Rect(32, 440, 356, 630)
# Full recessed panel opening in UI_Sidebar_Base (source coords).
COVER_REGION = pygame.Rect(24, 444, 372, 608)
PARTS_TOP_PADDING = 10


def _scale_region(region: pygame.Rect, scale: float) -> pygame.Rect:
    left = round(region.x * scale)
    top = round(region.y * scale)
    right = round((region.x + region.width) * scale)
    bottom = round((region.y + region.height) * scale)
    return pygame.Rect(left, top, right - left, bottom - top)


class BuildSidebar:
    SIDEBAR_IMAGE = "Sprites/UI_Sidebar_Base.png"

    def __init__(self, pilot: Pilot, part_defs, assets, screen_height: int):
        self.pilot = pilot
        self.assets = assets
        self._attr_font = pygame.font.SysFont(None, 20)
        self._portrait_surface = None

        base = pygame.image.load(self.SIDEBAR_IMAGE).convert_alpha()
        scale = screen_height / SOURCE_SIZE[1]
        self.width = int(SOURCE_SIZE[0] * scale)
        self.height = screen_height
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self._background = pygame.transform.smoothscale(base, (self.width, self.height))

        self.pilot_region = _scale_region(PILOT_REGION, scale)
        self.attr_region = _scale_region(ATTR_REGION, scale)
        parts_region = _scale_region(PARTS_REGION, scale)
        parts_content = parts_region.inflate(-16, -12)
        parts_content.y += int(PARTS_TOP_PADDING * scale)
        parts_content.height -= int(PARTS_TOP_PADDING * scale)

        self.palette = PartPalette(
            part_defs,
            assets,
            content_rect=parts_content,
            cover_rect=_scale_region(COVER_REGION, scale),
            draw_background=False,
            parts_per_row=5,
        )

        self._load_portrait()

    def _load_portrait(self):
        path = f"Sprites/pilots/{self.pilot.portrait_sprite}"
        image = pygame.image.load(path).convert_alpha()
        side = min(self.pilot_region.width, self.pilot_region.height) - 16
        self._portrait_surface = self._scale_to_square(image, side)

    @staticmethod
    def _scale_to_square(image: pygame.Surface, side: int) -> pygame.Surface:
        w, h = image.get_size()
        scale = min(side / w, side / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        scaled = pygame.transform.smoothscale(image, (new_w, new_h))

        surface = pygame.Surface((side, side), pygame.SRCALPHA)
        surface.blit(scaled, scaled.get_rect(center=(side // 2, side // 2)))
        return surface

    def _attribute_lines(self) -> list[str]:
        attributes = []
        attrs = self.pilot.attributes
        if attrs.fuel_consumption != 1.0:
            attributes.append(f"Fuel use: x{attrs.fuel_consumption:.1f}")
        if attrs.weight_reduction != 1.0:
            attributes.append(f"Weight reduction: x{attrs.weight_reduction:.1f}")
        if attrs.thrust_increase != 1.0:
            attributes.append(f"Thrust increase: x{attrs.thrust_increase:.1f}")
        if attrs.drag_efficiency != 1.0:
            attributes.append(f"Drag efficiency: x{attrs.drag_efficiency:.1f}")

        return attributes

    def update_hover(self, mouse_pos):
        self.palette.update_hover(mouse_pos)

    def item_at(self, pos):
        return self.palette.item_at(pos)

    def draw(self, surface):
        surface.blit(self._background, self.rect.topleft)

        portrait_rect = self._portrait_surface.get_rect(center=self.pilot_region.center)
        surface.blit(self._portrait_surface, portrait_rect)

        lines = [
            self._attr_font.render(line, True, (170, 185, 210))
            for line in self._attribute_lines()
        ]
        if lines:
            line_gap = 2
            block_height = sum(s.get_height() for s in lines) + line_gap * (len(lines) - 1)
            y = self.attr_region.y + (self.attr_region.height - block_height) // 2
            for line_surf in lines:
                line_rect = line_surf.get_rect(centerx=self.attr_region.centerx, top=y)
                surface.blit(line_surf, line_rect)
                y += line_surf.get_height() + line_gap

        self.palette.draw(surface)

    def draw_tooltip(self, surface):
        self.palette.draw_tooltip(surface)

    def lock_palette(self):
        self.palette.lock_palette()

    def unlock_palette(self):
        self.palette.unlock_palette()