import pygame

from rocket.pilot import Pilot
from ui.part_palette import PartPalette

SOURCE_SIZE = (420, 1080)
PILOT_REGION = pygame.Rect(32, 28, 356, 300)
ATTR_REGION = pygame.Rect(70, 355, 356, 88)
PARTS_REGION = pygame.Rect(32, 460, 356, 630)
PARTS_TOP_PADDING = 20


def _scale_region(region: pygame.Rect, scale: float) -> pygame.Rect:
    return pygame.Rect(
        int(region.x * scale),
        int(region.y * scale),
        int(region.width * scale),
        int(region.height * scale),
    )


class BuildSidebar:
    SIDEBAR_IMAGE = "Sprites/UI_Sidebar_Base.png"

    def __init__(self, pilot: Pilot, part_defs, assets, screen_height: int):
        self.pilot = pilot
        self.assets = assets
        self._name_font = pygame.font.SysFont(None, 28)
        self._attr_font = pygame.font.SysFont(None, 22)
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
            draw_background=False,
            parts_per_row=3,
        )

        self._load_portrait()

    def _load_portrait(self):
        path = f"Sprites/{self.pilot.portrait_sprite}"
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
        attrs = self.pilot.attributes
        return [
            f"Fuel use: x{attrs.fuel_consumption:.1f}",
        ]

    def update_hover(self, mouse_pos):
        self.palette.update_hover(mouse_pos)

    def item_at(self, pos):
        return self.palette.item_at(pos)

    def draw(self, surface):
        surface.blit(self._background, self.rect.topleft)

        portrait_rect = self._portrait_surface.get_rect(center=self.pilot_region.center)
        surface.blit(self._portrait_surface, portrait_rect)

        x = self.attr_region.x + 12
        y = self.attr_region.y + 8
        name_surf = self._name_font.render(self.pilot.name, True, (230, 236, 248))
        surface.blit(name_surf, (x, y))
        y += name_surf.get_height() + 4

        for line in self._attribute_lines():
            line_surf = self._attr_font.render(line, True, (170, 185, 210))
            surface.blit(line_surf, (x, y))
            y += line_surf.get_height() + 2

        self.palette.draw(surface)

    def draw_tooltip(self, surface):
        self.palette.draw_tooltip(surface)
